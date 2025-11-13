import { getGenerationById, getUserGenerations } from "../db";
import { StorageService } from "../services/storage";

export const Query = {
  // Phase 10+: Get generation status
  generationStatus: async (
    _: unknown,
    args: { jobId: string },
    context: any
  ) => {
    const generation = await getGenerationById(args.jobId);

    if (!generation) {
      throw new Error(`Generation ${args.jobId} not found`);
    }

    const storage = new StorageService();
    let audioUrl: string | null = null;
    let imageUrl: string | null = null;

    // Generate pre-signed URLs
    if (generation.image_key) {
      imageUrl = await storage.getImageReadUrl(generation.image_key);
    }

    if (generation.status === 'COMPLETE' && generation.audio_key) {
      audioUrl = await storage.getAudioReadUrl(generation.audio_key);
    }

    return {
      status: generation.status,
      audioUrl,
      imageUrl,
      errorMessage: generation.error_message,
      params: {
        genre: generation.genre,
        tempoBpm: generation.tempo_bpm,
        mood: String(generation.mood),
        scaleType: generation.scale_type,
      },
    };
  },

  // Phase 10+: Get user's generation history
  myGenerations: async (
    _: unknown,
    args: { limit?: number },
    context: any
  ) => {
    const userId = context.user?.id || 'default-user';
    const limit = args.limit ?? 20;

    const generations = await getUserGenerations(userId, limit);
    const storage = new StorageService();

    // Map to GraphQL response with pre-signed URLs
    return Promise.all(
      generations.map(async (gen) => {
        const imageUrl = await storage.getImageReadUrl(gen.image_key);
        const audioUrl = gen.audio_key
          ? await storage.getAudioReadUrl(gen.audio_key)
          : null;

        return {
          id: gen.id,
          userId: gen.user_id,
          imageKey: gen.image_key,
          audioKey: gen.audio_key,
          genre: gen.genre,
          tempoBpm: gen.tempo_bpm,
          status: gen.status,
          errorMessage: gen.error_message,
          createdAt: gen.created_at.toISOString(),
          imageUrl,
          audioUrl,
        };
      })
    );
  },
};
