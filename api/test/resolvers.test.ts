// Tests the API rules: the rate limit, scoping to the caller, upload before start, start only
// once, and putting the generation back if SQS fails. S3, SQS and MySQL are mocked.
import { beforeEach, describe, expect, it, vi } from "vitest";

// Fake S3: keys are built the same way as the real ones, links are fake URLs, and each test
// decides whether the uploaded image exists.
vi.mock("../src/aws/s3", () => ({
  imageKey: (id: string) => `images/${id}`,
  audioKey: (id: string) => `audio/${id}.wav`,
  signDownloadUrl: vi.fn(async (key: string) => `https://s3.example/${key}`),
  createUploadForm: vi.fn(),
  objectExists: vi.fn(),
}));
// Fake SQS: only the send is needed here; the tests check whether it was called.
vi.mock("../src/aws/queue", () => ({ enqueueJob: vi.fn() }));
// Fake MySQL: each query is a mock, so a test can choose what the database answers.
vi.mock("../src/db", () => ({
  countRecentGenerations: vi.fn(),
  deleteGeneration: vi.fn(),
  getGeneration: vi.fn(),
  insertGeneration: vi.fn(),
  listGenerations: vi.fn(),
  markPending: vi.fn(),
  markQueued: vi.fn(),
}));

import * as s3 from "../src/aws/s3";
import * as queue from "../src/aws/queue";
import * as db from "../src/db";
import { Context, resolvers } from "../src/resolvers";

const { Query, Mutation } = resolvers;
// The caller in every test. 203.0.113.7 is an address reserved for documentation.
const ME: Context = { clientId: "client-me", clientIp: "203.0.113.7" };

// A generations row as db.ts returns it, owned by ME unless a test overrides a field.
function row(overrides: Record<string, unknown> = {}) {
  return {
    id: "gen-1",
    client_id: ME.clientId,
    status: "PENDING",
    requested_genre: null,
    genre: null,
    confidence: null,
    error_message: null,
    created_at: new Date("2026-01-01T00:00:00Z"),
    ...overrides,
  } as never;
}

// The GraphQL error code a resolver threw, or undefined if it didn't throw.
async function errorCode(call: Promise<unknown>): Promise<unknown> {
  const error = await call.then(() => null, (thrown) => thrown);
  return error?.extensions?.code;
}

// By default every check passes: under the rate limit, row found, image uploaded, queueing works.
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(db.countRecentGenerations).mockResolvedValue(1);
  vi.mocked(db.getGeneration).mockResolvedValue(row());
  vi.mocked(db.markQueued).mockResolvedValue(true);
  vi.mocked(s3.objectExists).mockResolvedValue(true);
  vi.mocked(s3.createUploadForm).mockResolvedValue({ url: "https://s3.example/upload", fields: { key: "images/x" } });
});

describe("createGeneration", () => {
  // createGeneration saves the requested genre and signs a form for images/{id} with the right type.
  it("records the generation and returns an upload form", async () => {
    const result = await Mutation.createGeneration({}, { genre: "HOUSE", imageType: "PNG" }, ME);

    expect(db.insertGeneration).toHaveBeenCalledWith(expect.objectContaining({ ...ME, requestedGenre: "HOUSE" }));
    expect(s3.createUploadForm).toHaveBeenCalledWith(`images/${result.id}`, "image/png");
    expect(result.upload.fields).toEqual([{ name: "key", value: "images/x" }]);
  });

  // The insert-then-count rate limit in createGeneration (GENERATIONS_PER_HOUR). The refused
  // row is deleted, and no upload form is made for it.
  it("allows the 10th song in an hour but refuses the 11th and removes its row", async () => {
    vi.mocked(db.countRecentGenerations).mockResolvedValue(10);
    await Mutation.createGeneration({}, { imageType: "JPEG" }, ME);
    expect(db.deleteGeneration).not.toHaveBeenCalled();

    vi.mocked(db.countRecentGenerations).mockResolvedValue(11);
    expect(await errorCode(Mutation.createGeneration({}, { imageType: "JPEG" }, ME))).toBe("RATE_LIMITED");
    expect(db.deleteGeneration).toHaveBeenCalledOnce();
    expect(s3.createUploadForm).toHaveBeenCalledOnce();
  });
});

describe("startGeneration", () => {
  // The normal startGeneration path: PENDING to QUEUED, then one SQS message.
  it("queues an uploaded generation", async () => {
    await Mutation.startGeneration({}, { id: "gen-1" }, ME);

    expect(db.markQueued).toHaveBeenCalledWith("gen-1");
    expect(queue.enqueueJob).toHaveBeenCalledWith("gen-1", ME.clientId);
  });

  // findOwnGeneration: another browser's id gives the same NOT_FOUND as a missing one.
  it("treats another browser's generation as not found", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(row({ client_id: "someone-else" }));

    expect(await errorCode(Mutation.startGeneration({}, { id: "gen-1" }, ME))).toBe("NOT_FOUND");
    expect(queue.enqueueJob).not.toHaveBeenCalled();
  });

  // startGeneration checks objectExists, so the worker never looks for an image that isn't there.
  it("refuses to start before the image is uploaded", async () => {
    vi.mocked(s3.objectExists).mockResolvedValue(false);

    expect(await errorCode(Mutation.startGeneration({}, { id: "gen-1" }, ME))).toBe("BAD_REQUEST");
    expect(db.markQueued).not.toHaveBeenCalled();
  });

  // markQueued only moves a PENDING row, so a double click sends one message, not two.
  it("refuses to start the same generation twice", async () => {
    vi.mocked(db.markQueued).mockResolvedValue(false);

    expect(await errorCode(Mutation.startGeneration({}, { id: "gen-1" }, ME))).toBe("BAD_REQUEST");
    expect(queue.enqueueJob).not.toHaveBeenCalled();
  });

  // If enqueueJob throws, markPending undoes markQueued so the user can press start again.
  it("puts the generation back to PENDING if SQS is unavailable, so it can be started again", async () => {
    vi.mocked(queue.enqueueJob).mockRejectedValue(new Error("SQS unavailable"));

    await expect(Mutation.startGeneration({}, { id: "gen-1" }, ME)).rejects.toThrow("SQS unavailable");
    expect(db.markPending).toHaveBeenCalledWith("gen-1");
  });
});

describe("queries", () => {
  // The generation query returns null for someone else's row.
  it("hides another browser's generation", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(row({ client_id: "someone-else" }));

    expect(await Query.generation({}, { id: "gen-1" }, ME)).toBeNull();
  });

  // toGraphQLGeneration only signs an audio link for COMPLETED rows.
  it("only links the audio once the song is finished", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(row({ status: "COMPLETED", genre: "HOUSE" }));
    const done = await Query.generation({}, { id: "gen-1" }, ME);
    expect(done?.audioUrl).toBe("https://s3.example/audio/gen-1.wav");

    vi.mocked(db.getGeneration).mockResolvedValue(row({ status: "PROCESSING" }));
    expect((await Query.generation({}, { id: "gen-1" }, ME))?.audioUrl).toBeNull();
  });

  // myGenerations clamps limit to 1..MAX_HISTORY whatever the browser sends.
  it("keeps the history limit between 1 and 50", async () => {
    vi.mocked(db.listGenerations).mockResolvedValue([]);

    await Query.myGenerations({}, { limit: 1000 }, ME);
    await Query.myGenerations({}, { limit: -5 }, ME);

    expect(vi.mocked(db.listGenerations).mock.calls.map(([, limit]) => limit)).toEqual([50, 1]);
  });
});
