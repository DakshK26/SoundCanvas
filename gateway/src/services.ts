// http calls to the 3 internal services. they're all stateless, bytes/json in -> result out.
// checking the responses instead of trusting `as` casts - if a service sends back garbage I
// want the job to fail right here w/ a clear error, not 2 steps later somewhere confusing
import { requireEnv } from "./env";
import { Genre, GENRES } from "./schema";

const FEATURE_COUNT = 8;
const CPP_CORE_URL = requireEnv("CPP_CORE_URL");
const ML_URL = requireEnv("ML_URL");
const AUDIO_PRODUCER_URL = requireEnv("AUDIO_PRODUCER_URL");

// render is the slowest and it's well under a minute. no timeout + the heartbeat = a hung
// service would keep the job "alive" forever. so 2 min then give up and retry
const REQUEST_TIMEOUT_MS = 2 * 60 * 1000;

// thrown for 4xx - bad input, retrying won't help (e.g. corrupt image)
export class PermanentError extends Error {}

export interface Prediction {
  genre: Genre;
  confidence: number;
}

// the 4xx vs 5xx split is the whole retry strategy:
//   4xx -> PermanentError -> job fails now
//   5xx / timeout / network -> plain Error -> worker retries
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

// 8 numbers, all 0-1 (colour, brightness, contrast etc)
export async function extractFeatures(image: Buffer): Promise<number[]> {
  const response = await post(`${CPP_CORE_URL}/features`, image, "application/octet-stream");
  const { features } = (await response.json()) as { features?: unknown };
  if (!Array.isArray(features) || features.length !== FEATURE_COUNT || !features.every(isFraction)) {
    throw new Error(`cpp-core returned invalid features: ${JSON.stringify(features)}`);
  }
  return features;
}

// tf model -> genre + confidence
export async function predictGenre(features: number[]): Promise<Prediction> {
  const response = await post(`${ML_URL}/predict`, JSON.stringify({ features }), "application/json");
  const prediction = (await response.json()) as { genre?: unknown; confidence?: unknown };
  if (!GENRES.includes(prediction.genre as Genre) || !isFraction(prediction.confidence)) {
    throw new Error(`ml returned an invalid prediction: ${JSON.stringify(prediction)}`);
  }
  return prediction as Prediction;
}

// features + genre -> midi file bytes
export async function composeMidi(features: number[], genre: string): Promise<Buffer> {
  const response = await post(`${CPP_CORE_URL}/compose`, JSON.stringify({ features, genre }), "application/json");
  return Buffer.from(await response.arrayBuffer());
}

// midi -> mastered wav (the slow one)
export async function renderAudio(midi: Buffer, genre: string): Promise<Buffer> {
  const response = await post(`${AUDIO_PRODUCER_URL}/render?genre=${encodeURIComponent(genre)}`, midi, "audio/midi");
  return Buffer.from(await response.arrayBuffer());
}
