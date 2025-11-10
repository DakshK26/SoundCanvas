import path from "path";
import fs from "fs";

const DATA_ROOT = process.env.SC_DATA_ROOT || "/data";
const IMAGE_DIR = path.join(DATA_ROOT, "images");
const AUDIO_DIR = path.join(DATA_ROOT, "audio");

export function ensureStorageDirs() {
  [IMAGE_DIR, AUDIO_DIR].forEach((dir) => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });
}

export function getImagePath(filename: string): string {
  return path.join(IMAGE_DIR, filename);
}

export function getAudioPath(filename: string): string {
  return path.join(AUDIO_DIR, filename);
}

// Paths as returned to the client (keep them absolute inside containers)
export function relativeImagePathForDb(absPath: string): string {
  // For now, just store the absolute path; you can change this later if you want.
  return absPath;
}

export function relativeAudioPathForDb(absPath: string): string {
  return absPath;
}
