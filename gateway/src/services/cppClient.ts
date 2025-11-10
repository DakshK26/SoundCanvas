import axios from "axios";

const CPP_SERVICE_URL =
  process.env.CPP_SERVICE_URL || "http://cpp-core:8080/generate";

export type CppGenerateResponse = {
  audio_path: string;
  params: {
    tempoBpm: number;
    baseFrequency: number;
    brightness: number;
    volume: number;
    durationSeconds: number;
  };
};

export async function generateSoundViaCpp(
  imagePath: string,
  mode: "heuristic" | "model"
): Promise<CppGenerateResponse> {
  const payload = {
    image_path: imagePath,
    mode,
  };

  const res = await axios.post<CppGenerateResponse>(CPP_SERVICE_URL, payload, {
    timeout: 15000,
  });

  return res.data;
}
