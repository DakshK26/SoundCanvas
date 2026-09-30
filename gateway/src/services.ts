// The worker's HTTP calls to cpp-core, ml and audio-producer, which it finds by name through
// Cloud Map DNS. Every response is checked, so a broken service fails loudly instead of
// passing bad data further down the pipeline.
import { requireEnv } from "./env";
import { Genre, GENRES } from "./schema";

const FEATURE_COUNT = 8;
const CPP_CORE_URL = requireEnv("CPP_CORE_URL");
const ML_URL = requireEnv("ML_URL");
const AUDIO_PRODUCER_URL = requireEnv("AUDIO_PRODUCER_URL");

// Without a timeout the heartbeat would keep a hung service's job alive forever.
const REQUEST_TIMEOUT_MS = 2 * 60 * 1000;

// A 4xx from a service. Retrying the same input won't help.
export class PermanentError extends Error {}

export interface Prediction {
  genre: Genre;
  confidence: number;
}

// A 4xx becomes a PermanentError, so the job fails now. A 5xx, a network error or a timeout is a
// plain Error, so pipeline.ts retries it.
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

// The raw image bytes go straight in; the 8 numbers that come back feed both ml and /compose.
export async function extractFeatures(image: Buffer): Promise<number[]> {
  const response = await post(`${CPP_CORE_URL}/features`, image, "application/octet-stream");
  const { features } = (await response.json()) as { features?: unknown };
  if (!Array.isArray(features) || features.length !== FEATURE_COUNT || !features.every(isFraction)) {
    throw new Error(`cpp-core returned invalid features: ${JSON.stringify(features)}`);
  }
  return features;
}

// Skipped when the user already picked a genre. Confidence stays on the row for later retraining.
export async function predictGenre(features: number[]): Promise<Prediction> {
  const response = await post(`${ML_URL}/predict`, JSON.stringify({ features }), "application/json");
  const prediction = (await response.json()) as { genre?: unknown; confidence?: unknown };
  if (!GENRES.includes(prediction.genre as Genre) || !isFraction(prediction.confidence)) {
    throw new Error(`ml returned an invalid prediction: ${JSON.stringify(prediction)}`);
  }
  return prediction as Prediction;
}

// Same 8 features plus the genre; cpp-core turns them into a Standard MIDI File.
export async function composeMidi(features: number[], genre: string): Promise<Buffer> {
  const response = await post(`${CPP_CORE_URL}/compose`, JSON.stringify({ features, genre }), "application/json");
  return Buffer.from(await response.arrayBuffer());
}

// Genre is a query param so audio-producer can pick the drum kit and mix settings.
export async function renderAudio(midi: Buffer, genre: string): Promise<Buffer> {
  const response = await post(`${AUDIO_PRODUCER_URL}/render?genre=${encodeURIComponent(genre)}`, midi, "audio/midi");
  return Buffer.from(await response.arrayBuffer());
}
