/**
 * MusicGen Integration via Replicate API
 * 
 * Uses Meta's MusicGen model to generate high-quality music from text prompts.
 * Much better quality than MIDI + SoundFont rendering.
 */

import Replicate from 'replicate';

// Initialize Replicate client
const replicate = new Replicate({
    auth: process.env.REPLICATE_API_TOKEN,
});

export interface MusicGenOptions {
    prompt: string;
    duration?: number;  // seconds (max 30 for free tier)
    temperature?: number;  // creativity (0.5-1.5)
    topK?: number;
    topP?: number;
    classifier_free_guidance?: number;
    seed?: number;
}

export interface ImageAnalysis {
    genre: string;
    mood: string;
    energy: number;  // 0-1
    brightness: number;  // 0-1
    colors: string[];
}

/**
 * Generate a text prompt for MusicGen based on image analysis
 */
export function generateMusicPrompt(analysis: ImageAnalysis): string {
    const { genre, mood, energy, brightness, colors } = analysis;

    // Map genre to musical style
    const genreStyles: Record<string, string> = {
        'RAP': 'trap beat with 808 bass, hi-hats, dark synths',
        'RNB': 'smooth R&B with soft piano, warm bass, soulful melody',
        'HOUSE': 'house music with 4-on-floor kick, funky bassline, disco vibes',
        'EDM_CHILL': 'ambient electronic with soft pads, gentle arpeggios, relaxing melody',
        'EDM_DROP': 'high energy EDM with heavy bass drop, big synths, festival vibes',
        'RETROWAVE': 'synthwave with analog synths, gated drums, 80s nostalgia',
        'CINEMATIC': 'epic cinematic music with orchestral strings, dramatic percussion',
    };

    // Map energy to tempo/intensity descriptors
    const energyDescriptors = energy > 0.7 
        ? 'high energy, driving, intense'
        : energy > 0.4 
            ? 'medium tempo, groovy, balanced'
            : 'slow, relaxed, ambient';

    // Map brightness to tonal qualities
    const toneDescriptor = brightness > 0.6
        ? 'bright, uplifting, major key'
        : brightness > 0.3
            ? 'balanced, warm tones'
            : 'dark, moody, minor key';

    // Map mood
    const moodDescriptor = mood || 'atmospheric';

    // Build the prompt
    const style = genreStyles[genre] || genreStyles['EDM_CHILL'];
    
    const prompt = `${style}, ${energyDescriptors}, ${toneDescriptor}, ${moodDescriptor}, professional production quality, instrumental`;

    console.log(`[MusicGen] Generated prompt: ${prompt}`);
    return prompt;
}

/**
 * Generate music using MusicGen via Replicate
 */
export async function generateMusic(options: MusicGenOptions): Promise<string | null> {
    const {
        prompt,
        duration = 15,  // Default to 15 seconds
        temperature = 1.0,
        topK = 250,
        topP = 0.0,
        classifier_free_guidance = 3,
        seed,
    } = options;

    console.log(`[MusicGen] Generating music...`);
    console.log(`[MusicGen] Prompt: ${prompt}`);
    console.log(`[MusicGen] Duration: ${duration}s`);

    if (!process.env.REPLICATE_API_TOKEN) {
        console.error('[MusicGen] REPLICATE_API_TOKEN not set');
        return null;
    }

    try {
        // Use MusicGen large model for better quality
        const output = await replicate.run(
            "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055f2a4c4c78d3d10eba34ecd",
            {
                input: {
                    prompt,
                    duration,
                    temperature,
                    top_k: topK,
                    top_p: topP,
                    classifier_free_guidance,
                    ...(seed !== undefined && { seed }),
                    model_version: "stereo-large",  // Best quality
                    output_format: "wav",
                    normalization_strategy: "loudness",
                }
            }
        );

        // Output is a URL to the generated audio file
        const audioUrl = output as unknown as string;
        console.log(`[MusicGen] Generated audio URL: ${audioUrl}`);

        return audioUrl;
    } catch (error: any) {
        console.error(`[MusicGen] Error generating music:`, error.message);
        return null;
    }
}

/**
 * Download audio from URL and save to local file
 */
export async function downloadAudio(url: string, outputPath: string): Promise<boolean> {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const buffer = await response.arrayBuffer();
        const fs = await import('fs');
        await fs.promises.writeFile(outputPath, Buffer.from(buffer));

        console.log(`[MusicGen] Downloaded audio to: ${outputPath}`);
        return true;
    } catch (error: any) {
        console.error(`[MusicGen] Error downloading audio:`, error.message);
        return false;
    }
}

/**
 * Full pipeline: analyze image → generate prompt → generate music → save
 */
export async function generateMusicFromImageAnalysis(
    analysis: ImageAnalysis,
    outputPath: string,
    duration: number = 15
): Promise<boolean> {
    // Generate prompt from image analysis
    const prompt = generateMusicPrompt(analysis);

    // Generate music
    const audioUrl = await generateMusic({
        prompt,
        duration,
        temperature: 1.0,
    });

    if (!audioUrl) {
        console.error('[MusicGen] Failed to generate music');
        return false;
    }

    // Download and save
    const success = await downloadAudio(audioUrl, outputPath);
    return success;
}
