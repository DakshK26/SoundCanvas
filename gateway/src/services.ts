// One function per call the worker makes to the three internal microservices.
// Each service is stateless: bytes or JSON in, a result out.
import { requireEnv } from "./env";

const CPP_CORE_URL = requireEnv("CPP_CORE_URL");
const ML_URL = requireEnv("ML_URL");
const AUDIO_PRODUCER_URL = requireEnv("AUDIO_PRODUCER_URL");

// A job makes 4 calls; 4 x 2 minutes stays under the queue's 10-minute visibility
// timeout, so SQS never hands the same job to a second worker while one is still on it.
const REQUEST_TIMEOUT_MS = 2 * 60 * 1000;

/** An error that retrying cannot fix, such as an image that cannot be decoded. */
export class PermanentError extends Error {}

export interface Prediction {
  genre: string;
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

/** cpp-core measures the image: 8 numbers for color, brightness and contrast. */
export async function extractFeatures(image: Buffer): Promise<number[]> {
  const response = await post(`${CPP_CORE_URL}/features`, image, "application/octet-stream");
  const { features } = (await response.json()) as { features: number[] };
  return features;
}

/** The ml service's TensorFlow model picks a genre from the features. */
export async function predictGenre(features: number[]): Promise<Prediction> {
  const response = await post(`${ML_URL}/predict`, JSON.stringify({ features }), "application/json");
  return (await response.json()) as Prediction;
}

/** cpp-core composes a MIDI song for the features in the given genre. */
export async function composeMidi(features: number[], genre: string): Promise<Buffer> {
  const response = await post(`${CPP_CORE_URL}/compose`, JSON.stringify({ features, genre }), "application/json");
  return Buffer.from(await response.arrayBuffer());
}

/** audio-producer turns the MIDI into a mastered WAV. */
export async function renderAudio(midi: Buffer, genre: string): Promise<Buffer> {
  const response = await post(`${AUDIO_PRODUCER_URL}/render?genre=${genre}`, midi, "audio/midi");
  return Buffer.from(await response.arrayBuffer());
}
