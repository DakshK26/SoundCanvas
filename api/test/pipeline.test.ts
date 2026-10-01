// Tests the worker's decisions for one message: complete, fail now, retry, send to the DLQ,
// skip a duplicate, and keep the heartbeat going. S3, SQS, MySQL and the services are all mocked.
import { beforeEach, describe, expect, it, vi } from "vitest";

// Fake S3: the image download and WAV upload are mocks; the keys are built like the real ones.
vi.mock("../src/aws/s3", () => ({
  imageKey: (id: string) => `images/${id}`,
  audioKey: (id: string) => `audio/${id}.wav`,
  getObject: vi.fn(),
  putObject: vi.fn(),
}));
// Fake SQS: the tests check which of delete, release and extend the pipeline chose.
vi.mock("../src/aws/queue", () => ({ deleteJob: vi.fn(), releaseJob: vi.fn(), extendVisibility: vi.fn() }));
// Silence the JSON log lines during tests.
vi.mock("../src/log", () => ({ log: { info: vi.fn(), warn: vi.fn(), error: vi.fn() } }));
// Fake MySQL status updates.
vi.mock("../src/db", () => ({
  getGeneration: vi.fn(),
  markProcessing: vi.fn(),
  markCompleted: vi.fn(),
  markFailed: vi.fn(),
}));
// Fake cpp-core, ml and audio-producer. PermanentError is a real class so instanceof still works
// in handleMessage.
vi.mock("../src/serviceClients", async () => {
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
import * as services from "../src/serviceClients";
import { handleMessage, MAX_ATTEMPTS, RETRY_DELAY_SECONDS, VISIBILITY_TIMEOUT_SECONDS } from "../src/pipeline";

// Any 8 numbers between 0 and 1 will do.
const FEATURES = [0.5, 0.4, 0.3, 0.45, 0.6, 0.7, 0.2, 0.3];
// A received SQS message, as receiveJob in queue.ts returns it. receiveCount is the attempt number.
const message = (receiveCount = 1) => ({ generationId: "gen-1", receiptHandle: "handle", receiveCount });

function generationRow(requestedGenre: string | null = null) {
  return { id: "gen-1", status: "QUEUED", requested_genre: requestedGenre } as never;
}

// By default every step succeeds; each test breaks the one it cares about.
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(db.getGeneration).mockResolvedValue(generationRow());
  vi.mocked(db.markProcessing).mockResolvedValue(true);
  vi.mocked(s3.getObject).mockResolvedValue(Buffer.from("image"));
  vi.mocked(services.extractFeatures).mockResolvedValue(FEATURES);
  vi.mocked(services.predictGenre).mockResolvedValue({ genre: "HOUSE", confidence: 0.9 });
  vi.mocked(services.composeMidi).mockResolvedValue(Buffer.from("midi"));
  vi.mocked(services.renderAudio).mockResolvedValue(Buffer.from("wav"));
  vi.mocked(queue.extendVisibility).mockResolvedValue();
});

describe("handleMessage", () => {
  // Happy path in processJob: WAV saved at audio/{id}.wav, row COMPLETED, message deleted.
  it("completes a generation, saves the song and deletes the message", async () => {
    await handleMessage(message());

    expect(s3.putObject).toHaveBeenCalledWith("audio/gen-1.wav", Buffer.from("wav"), "audio/wav");
    expect(db.markCompleted).toHaveBeenCalledWith("gen-1", "HOUSE", 0.9, FEATURES);
    expect(queue.deleteJob).toHaveBeenCalledOnce();
    expect(queue.releaseJob).not.toHaveBeenCalled();
  });

  // requested_genre set: no ml call, and confidence is saved as null.
  it("skips the model when the user picked a genre", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(generationRow("HOUSE"));

    await handleMessage(message());

    expect(services.predictGenre).not.toHaveBeenCalled();
    expect(services.composeMidi).toHaveBeenCalledWith(FEATURES, "HOUSE");
    expect(db.markCompleted).toHaveBeenCalledWith("gen-1", "HOUSE", null, FEATURES);
  });

  // A PermanentError (a 4xx from a service) fails the row and deletes the message: no retries.
  it("fails straight away on bad input, without retrying", async () => {
    vi.mocked(services.extractFeatures).mockRejectedValue(new services.PermanentError("cannot decode image"));

    await handleMessage(message());

    expect(db.markFailed).toHaveBeenCalledWith("gen-1", "cannot decode image");
    expect(queue.deleteJob).toHaveBeenCalledOnce();
    expect(queue.releaseJob).not.toHaveBeenCalled();
  });

  // Any other error before the last attempt: release for RETRY_DELAY_SECONDS, row left PROCESSING.
  it("retries a temporary error later and leaves the generation running", async () => {
    vi.mocked(services.renderAudio).mockRejectedValue(new Error("audio-producer failed (503)"));

    await handleMessage(message(1));

    expect(queue.releaseJob).toHaveBeenCalledWith(message(1), RETRY_DELAY_SECONDS);
    expect(db.markFailed).not.toHaveBeenCalled();
    expect(queue.deleteJob).not.toHaveBeenCalled();
  });

  // Attempt MAX_ATTEMPTS: mark FAILED, release with no delay so SQS moves it to the DLQ (queue.tf).
  it("marks the generation failed on the last attempt and releases the message to the dead-letter queue", async () => {
    vi.mocked(services.renderAudio).mockRejectedValue(new Error("audio-producer failed (503)"));

    await handleMessage(message(MAX_ATTEMPTS));

    expect(db.markFailed).toHaveBeenCalledWith("gen-1", "audio-producer failed (503)");
    expect(queue.releaseJob).toHaveBeenCalledWith(message(MAX_ATTEMPTS), 0);
    expect(queue.deleteJob).not.toHaveBeenCalled();
  });

  // markProcessing returns false for a row that is already COMPLETED or FAILED, so nothing is redone.
  it("does nothing but delete a duplicate delivery of a finished generation", async () => {
    vi.mocked(db.markProcessing).mockResolvedValue(false);

    await handleMessage(message(2));

    expect(services.extractFeatures).not.toHaveBeenCalled();
    expect(db.markCompleted).not.toHaveBeenCalled();
    expect(queue.deleteJob).toHaveBeenCalledOnce();
  });

  // Fake timers: 150 seconds of a stuck render should give two heartbeats, and none after it ends.
  it("keeps the message hidden while a long job runs, and stops once it ends", async () => {
    vi.useFakeTimers();
    let finishRender: (wav: Buffer) => void = () => {};
    vi.mocked(services.renderAudio).mockReturnValue(new Promise((resolve) => { finishRender = resolve; }));

    const running = handleMessage(message());
    await vi.advanceTimersByTimeAsync(150_000);
    expect(queue.extendVisibility).toHaveBeenCalledTimes(2);
    expect(queue.extendVisibility).toHaveBeenCalledWith(message(), VISIBILITY_TIMEOUT_SECONDS);

    finishRender(Buffer.from("wav"));
    await running;
    await vi.advanceTimersByTimeAsync(120_000);
    expect(queue.extendVisibility).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });

  // A message for a deleted row is a PermanentError: nothing to retry.
  it("fails a message whose generation is not in the database", async () => {
    vi.mocked(db.getGeneration).mockResolvedValue(null);

    await handleMessage(message());

    expect(db.markFailed).toHaveBeenCalledOnce();
    expect(queue.deleteJob).toHaveBeenCalledOnce();
  });
});
