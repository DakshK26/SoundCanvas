import axios from 'axios';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { Readable } from 'stream';
import { getGenerationById, updateGenerationStatus, updateGenerationFields } from '../db';
import { StorageService } from './storage';
import Logger, { LogEvent } from '../utils/logger';

const CPP_CORE_URL = process.env.CPP_CORE_URL || 'http://localhost:8080';
const AUDIO_PRODUCER_URL = process.env.SC_AUDIO_PRODUCER_URL || process.env.AUDIO_PRODUCER_URL || 'http://localhost:9001';
const AWS_REGION = process.env.AWS_REGION || 'us-east-2';
const S3_BUCKET_NAME = process.env.S3_BUCKET_NAME || '';

// Initialize S3 Client
const s3Client = new S3Client({
    region: AWS_REGION,
    credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
    },
});

export class OrchestratorService {
    /**
     * Main orchestration pipeline
     * 1. Download image from S3
     * 2. Call cpp-core for MIDI generation
     * 3. Call audio-producer for WAV rendering
     * 4. Upload WAV to S3
     * 5. Update DB with final status
     */
    async processGeneration(jobId: string, userId?: string): Promise<void> {
        const uid = userId || 'default-user';

        Logger.info('Starting generation pipeline', {
            jobId,
            userId: uid,
            event: LogEvent.JOB_STARTED,
        });

        const generation = await getGenerationById(jobId);
        if (!generation) {
            throw new Error(`Generation ${jobId} not found`);
        }

        // Use shared volume instead of temp directory
        const dataRoot = process.env.SC_DATA_ROOT || '/data';
        const tempDir = path.join(dataRoot, 'temp', jobId);
        await fs.promises.mkdir(tempDir, { recursive: true });

        const imagePath = path.join(tempDir, 'input.jpg');
        const midiPath = path.join(tempDir, 'composition.mid');
        const audioPath = path.join(tempDir, 'output.wav');

        try {
            // Step 1: Download image from S3
            console.log(`[Orchestrator] [${jobId}] Downloading image from S3: ${generation.image_key}`);
            await this.downloadFromS3(generation.image_key, imagePath);

            // Step 2: Call cpp-core service
            console.log(`[Orchestrator] [${jobId}] Calling cpp-core service...`);
            const cppResponse = await this.callCppCore(imagePath, generation.genre, generation.mode);

            // Phase 12 A2.2: Update tempo, scale, AND decided genre in DB
            // Don't change status (already RUNNING), just update fields
            await updateGenerationFields(jobId, {
                tempo_bpm: cppResponse.tempoBpm,
                scale_type: cppResponse.scaleType,
                genre: cppResponse.decidedGenre || generation.genre
            });

            if (cppResponse.decidedGenre && cppResponse.decidedGenre !== 'auto') {
                console.log(`[Orchestrator] Genre decided by cpp-core: ${cppResponse.decidedGenre}`);
            }

            // Step 3: Call audio-producer service
            console.log(`[Orchestrator] [${jobId}] Calling audio-producer service...`);
            await this.callAudioProducer(cppResponse.midiPath || midiPath, audioPath, cppResponse.decidedGenre || generation.genre);

            // Phase 12 A1.3: Validate audio file before S3 upload
            const audioStats = await fs.promises.stat(audioPath);
            console.log(`[Orchestrator] Local audio file: ${audioStats.size} bytes`);

            if (audioStats.size === 0) {
                throw new Error('Generated audio file is zero bytes');
            }

            if (audioStats.size < 1000) {
                console.warn(`[Orchestrator] Warning: Audio file suspiciously small (${audioStats.size} bytes)`);
            }

            // Step 4: Upload audio to S3
            const audioKey = `audio/${generation.user_id}/${jobId}/output.wav`;
            console.log(`[Orchestrator] [${jobId}] Uploading audio to S3: ${audioKey}`);
            await this.uploadToS3(audioPath, audioKey, 'audio/wav');

            // Phase 12 A1.3: Verify S3 upload succeeded
            console.log(`[Orchestrator] Uploaded ${audioStats.size} bytes to S3: ${audioKey}`);

            // Step 5: Mark as complete
            await updateGenerationStatus(jobId, 'COMPLETE', {
                audio_key: audioKey,
            });

            console.log(`[Orchestrator] [${jobId}] Generation completed successfully`);
        } catch (error: any) {
            console.error(`[Orchestrator] [${jobId}] Generation failed:`, error);

            // Provide user-friendly error messages
            let userMessage = 'An unexpected error occurred during generation.';

            if (error.code === 'ECONNREFUSED') {
                userMessage = 'Service temporarily unavailable. Please try again in a moment.';
            } else if (error.code === 'ETIMEDOUT') {
                userMessage = 'Generation timed out. The image might be too complex. Please try a different image.';
            } else if (error.message.includes('Audio file is empty')) {
                userMessage = 'Audio rendering failed. Please try again with a different image or genre.';
            } else if (error.message.includes('S3')) {
                userMessage = 'Failed to upload results. Please check your connection and try again.';
            } else if (error.message.includes('state transition')) {
                userMessage = 'Generation already in progress or completed. Please refresh the page.';
            } else {
                // Use the original error message if it's descriptive
                userMessage = error.message || userMessage;
            }

            await updateGenerationStatus(jobId, 'FAILED', {
                error_message: userMessage,
            });
            throw error;
        } finally {
            // Cleanup temp files
            try {
                await fs.promises.rm(tempDir, { recursive: true, force: true });
            } catch (err) {
                console.warn(`[Orchestrator] Failed to cleanup temp dir: ${tempDir}`);
            }
        }
    }

    /**
     * Download file from S3 to local path
     */
    private async downloadFromS3(key: string, localPath: string): Promise<void> {
        const command = new GetObjectCommand({
            Bucket: S3_BUCKET_NAME,
            Key: key,
        });

        const response = await s3Client.send(command);

        if (!response.Body) {
            throw new Error('No body in S3 response');
        }

        // Stream to file
        const stream = response.Body as Readable;
        const writeStream = fs.createWriteStream(localPath);

        await new Promise<void>((resolve, reject) => {
            stream.pipe(writeStream);
            stream.on('error', reject);
            writeStream.on('finish', () => resolve());
            writeStream.on('error', reject);
        });
    }

    /**
     * Upload file from local path to S3
     */
    private async uploadToS3(localPath: string, key: string, contentType: string): Promise<void> {
        const fileContent = await fs.promises.readFile(localPath);

        const command = new PutObjectCommand({
            Bucket: S3_BUCKET_NAME,
            Key: key,
            Body: fileContent,
            ContentType: contentType,
            // Add CORS headers for browser access
            CacheControl: 'max-age=31536000',
            Metadata: {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, HEAD',
            },
        });

        await s3Client.send(command);
    }

    /**
     * Call cpp-core service for MIDI generation
     */
    private async callCppCore(imagePath: string, genre: string, mode: string): Promise<{
        midiPath?: string;
        tempoBpm: number;
        scaleType: string;
        decidedGenre?: string;  // Phase 12 A2.2: Capture decided genre
    }> {
        const cppCoreUrl = process.env.CPP_SERVICE_URL || process.env.CPP_CORE_URL || 'http://localhost:8080';

        console.log(`[Orchestrator] Calling cpp-core service at ${cppCoreUrl}`);

        try {
            const response = await fetch(`${cppCoreUrl}/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image_path: imagePath,
                    mode: mode,
                    genre: genre,  // Note: cpp-core may ignore this and decide its own
                }),
            });

            if (!response.ok) {
                throw new Error(`cpp-core returned ${response.status}: ${await response.text()}`);
            }

            const data = await response.json();

            console.log(`[Orchestrator] cpp-core response:`, data);

            return {
                midiPath: data.midi_path,
                tempoBpm: data.tempo_bpm || 120,
                scaleType: data.scale_type || 'minor',
                decidedGenre: data.decided_genre,  // Phase 12 A2.2: Capture decided genre!
            };
        } catch (error) {
            console.error(`[Orchestrator] cpp-core call failed:`, error);
            throw new Error(`Failed to call cpp-core service: ${error}`);
        }
    }

    /**
     * Call audio-producer service for WAV rendering
     */
    private async callAudioProducer(midiPath: string, outputPath: string, genre: string = 'EDM_DROP'): Promise<void> {
        const audioProducerUrl = AUDIO_PRODUCER_URL;

        console.log(`[Orchestrator] Calling audio-producer at ${audioProducerUrl}/produce`);
        console.log(`[Orchestrator] MIDI path: ${midiPath}, Output path: ${outputPath}, Genre: ${genre}`);

        try {
            const response = await axios.post(`${audioProducerUrl}/produce`, {
                midi_path: midiPath,
                output_path: outputPath,
                genre: genre,
                apply_mastering: true,
                use_sample_drums: true,
                render_fx: true,
            }, {
                timeout: 120000, // 2 minutes timeout for audio rendering
            });

            if (response.status !== 200) {
                throw new Error(`Audio producer returned status ${response.status}: ${response.statusText}`);
            }

            console.log(`[Orchestrator] Audio rendering completed:`, response.data);

            // Verify the output file exists and has content
            const stats = await fs.promises.stat(outputPath);
            if (stats.size < 1000) {
                throw new Error(`Audio producer created file but it's too small: ${stats.size} bytes`);
            }

            console.log(`[Orchestrator] Rendered audio file: ${stats.size} bytes`);
        } catch (error: any) {
            console.error(`[Orchestrator] Audio producer error:`, error.message);
            throw new Error(`Failed to render audio: ${error.message}`);
        }
    }
}
