import { FileUpload } from "graphql-upload-minimal";
import { generateSoundViaCpp } from "../services/cppClient";
import {
  ensureStorageDirs,
  getImagePath,
  relativeImagePathForDb,
  relativeAudioPathForDb,
  StorageService,
} from "../services/storage";
import { dbInsertSoundGeneration, insertGeneration, updateGenerationStatus } from "../db";
import { OrchestratorService } from "../services/orchestrator";
import { v4 as uuidv4 } from "uuid";

type SoundMode = "HEURISTIC" | "MODEL";

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

  // ============================================================================
  // Phase 10: New S3-based workflow
  // ============================================================================
  createGeneration: async (
    _: unknown,
    args: { input: { genreOverride?: string; mode?: string } },
    context: any
  ) => {
    const jobId = uuidv4();
    const userId = context.user?.id || 'default-user';
    const genre = args.input.genreOverride || 'auto';
    const mode = args.input.mode || 'model';

    // Generate S3 pre-signed upload URL
    const storage = new StorageService();
    const imageKey = storage.getImageKey(userId, jobId);
    const uploadUrl = await storage.getImageUploadUrl(userId, jobId);

    // Create database record
    await insertGeneration({
      id: jobId,
      user_id: userId,
      image_key: imageKey,
      genre: genre,
      mode: mode as 'heuristic' | 'model',
    });

    return {
      jobId,
      imageUploadUrl: uploadUrl,
      imageId: imageKey,
    };
  },

  startGeneration: async (
    _: unknown,
    args: { jobId: string },
    context: any
  ) => {
    const { jobId } = args;

    // Update status to RUNNING
    await updateGenerationStatus(jobId, 'RUNNING');

    // Trigger async processing (fire and forget)
    processGeneration(jobId).catch(async (err) => {
      console.error(`Generation ${jobId} failed:`, err);
      await updateGenerationStatus(jobId, 'FAILED', {
        error_message: err.message || 'Unknown error',
      });
    });

    return { success: true };
  },
};

// ============================================================================
// Async generation pipeline
// ============================================================================
async function processGeneration(jobId: string) {
  const orchestrator = new OrchestratorService();
  await orchestrator.processGeneration(jobId);
}