// One function per call the worker makes to the three internal microservices.
// Each service is stateless: bytes or JSON in, a result out.
import { requireEnv } from "./env";

const CPP_CORE_URL = requireEnv("CPP_CORE_URL");
const ML_URL = requireEnv("ML_URL");
const AUDIO_PRODUCER_URL = requireEnv("AUDIO_PRODUCER_URL");

export interface Prediction {
  genre: string;
  confidence: number;
}

/** POSTs a body and returns the response, throwing if the service reports an error. */
async function post(url: string, body: Buffer | string, contentType: string): Promise<Response> {
  const response = await fetch(url, { method: "POST", body, headers: { "Content-Type": contentType } });
  if (!response.ok) throw new Error(`${url} returned ${response.status}: ${await response.text()}`);
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
