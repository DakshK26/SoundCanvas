import { generateSoundViaCpp } from "../services/cppClient";
import {
  ensureStorageDirs,
  getImagePath,
  relativeImagePathForDb,
  relativeAudioPathForDb,
} from "../services/storage";
import { dbInsertSoundGeneration } from "../db";

type SoundMode = "HEURISTIC" | "MODEL";

interface FileUpload {
  filename: string;
  mimetype: string;
  encoding: string;
  createReadStream: () => NodeJS.ReadableStream;
}

export const Mutation = {
  uploadAndGenerateSound: async (
    _: unknown,
    args: { file: Promise<FileUpload>; mode: SoundMode }
  ) => {
    ensureStorageDirs();

    const { createReadStream, filename, mimetype } = await args.file;

    if (!mimetype.startsWith("image/")) {
      throw new Error("Uploaded file must be an image");
    }

    const mode = args.mode === "HEURISTIC" ? "heuristic" : "model";

    // Save image to disk
    const imageFilename = Date.now() + "_" + filename.replace(/\s+/g, "_");
    const imagePath = getImagePath(imageFilename);

    await new Promise<void>((resolve, reject) => {
      const stream = createReadStream();
      const out = require("fs").createWriteStream(imagePath);
      stream
        .pipe(out)
        .on("finish", () => resolve())
        .on("error", (err: Error) => reject(err));
    });

    // Call C++ service
    const cppResp = await generateSoundViaCpp(imagePath, mode);

    const dbRecord = await dbInsertSoundGeneration({
      imagePath: relativeImagePathForDb(imagePath),
      audioPath: relativeAudioPathForDb(cppResp.audio_path),
      mode,
      params: cppResp.params,
    });

    return dbRecord;
  },
};
