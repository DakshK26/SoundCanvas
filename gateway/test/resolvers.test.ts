import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/aws/s3", () => ({
  imageKey: (id: string) => `images/${id}`,
  audioKey: (id: string) => `audio/${id}.wav`,
  downloadUrl: vi.fn(async (key: string) => `https://s3.example/${key}`),
  uploadForm: vi.fn(),
  objectExists: vi.fn(),
}));
vi.mock("../src/aws/queue", () => ({ enqueueJob: vi.fn() }));
vi.mock("../src/db", () => ({
  countRecentGenerations: vi.fn(),
  deleteGeneration: vi.fn(),
  getGeneration: vi.fn(),
  insertGeneration: vi.fn(),
  listGenerations: vi.fn(),
  markPending: vi.fn(),
  markQueued: vi.fn(),
  setFeedback: vi.fn(),
}));

import * as s3 from "../src/aws/s3";
import * as queue from "../src/aws/queue";
import * as db from "../src/db";
import { Context, resolvers } from "../src/resolvers";

const { Query, Mutation } = resolvers;
const ME: Context = { clientId: "client-me", clientIp: "203.0.113.7" };

function row(overrides: Record<string, unknown> = {}) {
  return {
    id: "job-1",
    client_id: ME.clientId,
    status: "PENDING",
    requested_genre: null,
    genre: null,
    confidence: null,
    feedback: null,
    error_message: null,
    created_at: new Date("2026-01-01T00:00:00Z"),
    ...overrides,
  } as never;
}

async function errorCode(call: Promise<unknown>): Promise<unknown> {
  const error = await call.then(() => null, (thrown) => thrown);
  return error?.extensions?.code;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(db.countRecentGenerations).mockResolvedValue(1);
  vi.mocked(db.getGeneration).mockResolvedValue(row());
  vi.mocked(db.markQueued).mockResolvedValue(true);
  vi.mocked(s3.objectExists).mockResolvedValue(true);
  vi.mocked(s3.uploadForm).mockResolvedValue({ url: "https://s3.example/upload", fields: { key: "images/x" } });
});

describe("createGeneration", () => {
  it("records the job and returns an upload form", async () => {
    const result = await Mutation.createGeneration({}, { genre: "HOUSE", imageType: "PNG" }, ME);

    expect(db.insertGeneration).toHaveBeenCalledWith(expect.objectContaining({ ...ME, requestedGenre: "HOUSE" }));
    expect(s3.uploadForm).toHaveBeenCalledWith(`images/${result.jobId}`, "image/png");
    expect(result.upload.fields).toEqual([{ name: "key", value: "images/x" }]);
  });

  it("allows the 10th song in an hour but refuses the 11th and removes its row", async () => {
    vi.mocked(db.countRecentGenerations).mockResolvedValue(10);
    await Mutation.createGeneration({}, { imageType: "JPEG" }, ME);
    expect(db.deleteGeneration).not.toHaveBeenCalled();

    vi.mocked(db.countRecentGenerations).mockResolvedValue(11);
    expect(await errorCode(Mutation.createGeneration({}, { imageType: "JPEG" }, ME))).toBe("RATE_LIMITED");
    expect(db.deleteGeneration).toHaveBeenCalledOnce();
    expect(s3.uploadForm).toHaveBeenCalledOnce();
  });
});

describe("startGeneration", () => {
  it("queues an uploaded job", async () => {
    await Mutation.startGeneration({}, { jobId: "job-1" }, ME);

    expect(db.markQueued).toHaveBeenCalledWith("job-1");
    expect(queue.enqueueJob).toHaveBeenCalledWith("job-1", ME.clientId);
  });

  it("treats another browser's job as not found", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(row({ client_id: "someone-else" }));

    expect(await errorCode(Mutation.startGeneration({}, { jobId: "job-1" }, ME))).toBe("NOT_FOUND");
    expect(queue.enqueueJob).not.toHaveBeenCalled();
  });

  it("refuses to start before the image is uploaded", async () => {
    vi.mocked(s3.objectExists).mockResolvedValue(false);

    expect(await errorCode(Mutation.startGeneration({}, { jobId: "job-1" }, ME))).toBe("BAD_REQUEST");
    expect(db.markQueued).not.toHaveBeenCalled();
  });

  it("refuses to start the same job twice", async () => {
    vi.mocked(db.markQueued).mockResolvedValue(false);

    expect(await errorCode(Mutation.startGeneration({}, { jobId: "job-1" }, ME))).toBe("BAD_REQUEST");
    expect(queue.enqueueJob).not.toHaveBeenCalled();
  });

  it("puts the job back to PENDING if SQS is unavailable, so it can be started again", async () => {
    vi.mocked(queue.enqueueJob).mockRejectedValue(new Error("SQS unavailable"));

    await expect(Mutation.startGeneration({}, { jobId: "job-1" }, ME)).rejects.toThrow("SQS unavailable");
    expect(db.markPending).toHaveBeenCalledWith("job-1");
  });
});

describe("queries", () => {
  it("hides another browser's job", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(row({ client_id: "someone-else" }));

    expect(await Query.generation({}, { jobId: "job-1" }, ME)).toBeNull();
  });

  it("only links the audio once the song is finished", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(row({ status: "COMPLETED", genre: "HOUSE" }));
    const done = await Query.generation({}, { jobId: "job-1" }, ME);
    expect(done?.audioUrl).toBe("https://s3.example/audio/job-1.wav");

    vi.mocked(db.getGeneration).mockResolvedValue(row({ status: "PROCESSING" }));
    expect((await Query.generation({}, { jobId: "job-1" }, ME))?.audioUrl).toBeNull();
  });

  it("keeps the history limit between 1 and 50", async () => {
    vi.mocked(db.listGenerations).mockResolvedValue([]);

    await Query.myGenerations({}, { limit: 1000 }, ME);
    await Query.myGenerations({}, { limit: -5 }, ME);

    expect(vi.mocked(db.listGenerations).mock.calls.map(([, limit]) => limit)).toEqual([50, 1]);
  });
});

describe("rateGeneration", () => {
  it("refuses feedback the database did not accept (not yours, or not finished)", async () => {
    vi.mocked(db.setFeedback).mockResolvedValue(false);

    expect(await errorCode(Mutation.rateGeneration({}, { jobId: "job-1", feedback: "UP" }, ME))).toBe("BAD_REQUEST");
  });
});
