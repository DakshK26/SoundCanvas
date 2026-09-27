// One function per call the worker makes to the three internal microservices.
// Each service is stateless: bytes or JSON in, a result out.
// Responses are checked before use, so a service returning the wrong shape fails the
// job with a clear message instead of passing bad data further down the pipeline.
import { requireEnv } from "./env";
import { Genre, GENRES } from "./schema";

const FEATURE_COUNT = 8;
const CPP_CORE_URL = requireEnv("CPP_CORE_URL");
const ML_URL = requireEnv("ML_URL");
const AUDIO_PRODUCER_URL = requireEnv("AUDIO_PRODUCER_URL");

// The slowest call, rendering, finishes well within a minute. A service that has not answered in
// 2 minutes is treated as hung: the attempt fails and is retried, rather than the worker's
// visibility heartbeat keeping a stuck job alive forever.
const REQUEST_TIMEOUT_MS = 2 * 60 * 1000;

/** An error that retrying cannot fix, such as an image that cannot be decoded. */
export class PermanentError extends Error {}

export interface Prediction {
  genre: Genre;
  confidence: number;
}

/**
 * POSTs a body and returns the response.
 * A 4xx answer means the input was bad (PermanentError). A 5xx answer, a timeout
 * or a network error is thrown as a plain Error, which the worker retries.
 */
async function post(url: string, body: Buffer | string, contentType: string): Promise<Response> {
  const response = await fetch(url, {
    method: "POST",
    body,
    headers: { "Content-Type": contentType },
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  if (response.status >= 400 && response.status < 500) {
    throw new PermanentError(`${url} rejected the request (${response.status}): ${await response.text()}`);
  }
  if (!response.ok) throw new Error(`${url} failed (${response.status}): ${await response.text()}`);
  return response;
}

const isFraction = (value: unknown) => typeof value === "number" && value >= 0 && value <= 1;

/** cpp-core measures the image: 8 numbers from 0 to 1 for color, brightness and contrast. */
export async function extractFeatures(image: Buffer): Promise<number[]> {
  const response = await post(`${CPP_CORE_URL}/features`, image, "application/octet-stream");
  const { features } = (await response.json()) as { features?: unknown };
  if (!Array.isArray(features) || features.length !== FEATURE_COUNT || !features.every(isFraction)) {
    throw new Error(`cpp-core returned invalid features: ${JSON.stringify(features)}`);
  }
  return features;
}

/** The ml service's TensorFlow model picks a genre from the features. */
export async function predictGenre(features: number[]): Promise<Prediction> {
  const response = await post(`${ML_URL}/predict`, JSON.stringify({ features }), "application/json");
  const prediction = (await response.json()) as { genre?: unknown; confidence?: unknown };
  if (!GENRES.includes(prediction.genre as Genre) || !isFraction(prediction.confidence)) {
    throw new Error(`ml returned an invalid prediction: ${JSON.stringify(prediction)}`);
  }
  return prediction as Prediction;
}

/** cpp-core composes a MIDI song for the features in the given genre. */
export async function composeMidi(features: number[], genre: string): Promise<Buffer> {
  const response = await post(`${CPP_CORE_URL}/compose`, JSON.stringify({ features, genre }), "application/json");
  return Buffer.from(await response.arrayBuffer());
}

/** audio-producer turns the MIDI into a mastered WAV. */
export async function renderAudio(midi: Buffer, genre: string): Promise<Buffer> {
  const response = await post(`${AUDIO_PRODUCER_URL}/render?genre=${encodeURIComponent(genre)}`, midi, "audio/midi");
  return Buffer.from(await response.arrayBuffer());
}
