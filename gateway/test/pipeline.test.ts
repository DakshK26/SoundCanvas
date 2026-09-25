// Tests for the worker's decisions (src/pipeline.ts). S3, SQS, MySQL and the
// three services are replaced with mocks, so these run without AWS or Docker.
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/aws/s3", () => ({
  imageKey: (id: string) => `images/${id}`,
  audioKey: (id: string) => `audio/${id}.wav`,
  getObject: vi.fn(),
  putObject: vi.fn(),
}));
vi.mock("../src/aws/queue", () => ({ deleteJob: vi.fn(), releaseJob: vi.fn(), extendVisibility: vi.fn() }));
vi.mock("../src/log", () => ({ log: { info: vi.fn(), warn: vi.fn(), error: vi.fn() } }));
vi.mock("../src/db", () => ({
  getGeneration: vi.fn(),
  startProcessing: vi.fn(),
  markCompleted: vi.fn(),
  markFailed: vi.fn(),
}));
vi.mock("../src/services", async () => {
  class PermanentError extends Error {}
  return {
    PermanentError,
    extractFeatures: vi.fn(),
    predictGenre: vi.fn(),
    composeMidi: vi.fn(),
    renderAudio: vi.fn(),
  };
});

import * as s3 from "../src/aws/s3";
import * as queue from "../src/aws/queue";
import * as db from "../src/db";
import * as services from "../src/services";
import { handleMessage, MAX_ATTEMPTS, RETRY_DELAY_SECONDS, VISIBILITY_TIMEOUT_SECONDS } from "../src/pipeline";

const FEATURES = [0.5, 0.4, 0.3, 0.45, 0.6, 0.7, 0.2, 0.3];
const message = (receiveCount = 1) => ({ jobId: "job-1", receiptHandle: "handle", receiveCount });

function jobRow(requestedGenre: string | null = null) {
  return { id: "job-1", status: "QUEUED", requested_genre: requestedGenre } as never;
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(db.getGeneration).mockResolvedValue(jobRow());
  vi.mocked(db.startProcessing).mockResolvedValue(true);
  vi.mocked(s3.getObject).mockResolvedValue(Buffer.from("image"));
  vi.mocked(services.extractFeatures).mockResolvedValue(FEATURES);
  vi.mocked(services.predictGenre).mockResolvedValue({ genre: "HOUSE", confidence: 0.9 });
  vi.mocked(services.composeMidi).mockResolvedValue(Buffer.from("midi"));
  vi.mocked(services.renderAudio).mockResolvedValue(Buffer.from("wav"));
  vi.mocked(queue.extendVisibility).mockResolvedValue();
});

describe("handleMessage", () => {
  it("completes a job, saves the song and deletes the message", async () => {
    await handleMessage(message());

    expect(s3.putObject).toHaveBeenCalledWith("audio/job-1.wav", Buffer.from("wav"), "audio/wav");
    expect(db.markCompleted).toHaveBeenCalledWith("job-1", "HOUSE", 0.9, FEATURES);
    expect(queue.deleteJob).toHaveBeenCalledOnce();
    expect(queue.releaseJob).not.toHaveBeenCalled();
  });

  it("skips the model when the user picked a genre", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(jobRow("RETROWAVE"));

    await handleMessage(message());

    expect(services.predictGenre).not.toHaveBeenCalled();
    expect(services.composeMidi).toHaveBeenCalledWith(FEATURES, "RETROWAVE");
    expect(db.markCompleted).toHaveBeenCalledWith("job-1", "RETROWAVE", null, FEATURES);
  });

  it("fails straight away on bad input, without retrying", async () => {
    vi.mocked(services.extractFeatures).mockRejectedValue(new services.PermanentError("cannot decode image"));

    await handleMessage(message());

    expect(db.markFailed).toHaveBeenCalledWith("job-1", "cannot decode image");
    expect(queue.deleteJob).toHaveBeenCalledOnce();
    expect(queue.releaseJob).not.toHaveBeenCalled();
  });

  it("retries a temporary error later and leaves the job running", async () => {
    vi.mocked(services.renderAudio).mockRejectedValue(new Error("audio-producer failed (503)"));

    await handleMessage(message(1));

    expect(queue.releaseJob).toHaveBeenCalledWith(message(1), RETRY_DELAY_SECONDS);
    expect(db.markFailed).not.toHaveBeenCalled();
    expect(queue.deleteJob).not.toHaveBeenCalled();
  });

  it("marks the job failed on the last attempt and releases the message to the dead-letter queue", async () => {
    vi.mocked(services.renderAudio).mockRejectedValue(new Error("audio-producer failed (503)"));

    await handleMessage(message(MAX_ATTEMPTS));

    expect(db.markFailed).toHaveBeenCalledWith("job-1", "audio-producer failed (503)");
    expect(queue.releaseJob).toHaveBeenCalledWith(message(MAX_ATTEMPTS), 0);
    expect(queue.deleteJob).not.toHaveBeenCalled();
  });

  it("does nothing but delete a duplicate delivery of a finished job", async () => {
    vi.mocked(db.startProcessing).mockResolvedValue(false);

    await handleMessage(message(2));

    expect(services.extractFeatures).not.toHaveBeenCalled();
    expect(db.markCompleted).not.toHaveBeenCalled();
    expect(queue.deleteJob).toHaveBeenCalledOnce();
  });

  it("keeps the message hidden while a long job runs, and stops once it ends", async () => {
    vi.useFakeTimers();
    let finishRender: (wav: Buffer) => void = () => {};
    vi.mocked(services.renderAudio).mockReturnValue(new Promise((resolve) => { finishRender = resolve; }));

    const running = handleMessage(message());
    await vi.advanceTimersByTimeAsync(150_000); // two and a half minutes into rendering
    expect(queue.extendVisibility).toHaveBeenCalledTimes(2);
    expect(queue.extendVisibility).toHaveBeenCalledWith(message(), VISIBILITY_TIMEOUT_SECONDS);

    finishRender(Buffer.from("wav"));
    await running;
    await vi.advanceTimersByTimeAsync(120_000);
    expect(queue.extendVisibility).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });

  it("fails a message whose job is not in the database", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(null);

    await handleMessage(message());

    expect(db.markFailed).toHaveBeenCalledOnce();
    expect(queue.deleteJob).toHaveBeenCalledOnce();
  });
});
