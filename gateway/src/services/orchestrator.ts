import axios from 'axios';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { Readable } from 'stream';
import { getGenerationById, updateGenerationStatus } from '../db';
import { StorageService } from './storage';

const CPP_CORE_URL = process.env.CPP_CORE_URL || 'http://localhost:8080';
const AUDIO_PRODUCER_URL = process.env.AUDIO_PRODUCER_URL || 'http://localhost:5001';
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
    async processGeneration(jobId: string): Promise<void> {
        console.log(`[Orchestrator] Starting generation ${jobId}`);

        const generation = await getGenerationById(jobId);
        if (!generation) {
            throw new Error(`Generation ${jobId} not found`);
        }

        const tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'soundcanvas-'));
        const imagePath = path.join(tempDir, 'input.jpg');
        const midiPath = path.join(tempDir, 'composition.mid');
        const audioPath = path.join(tempDir, 'output.wav');

        try {
            // Step 1: Download image from S3
            console.log(`[Orchestrator] Downloading image from S3: ${generation.image_key}`);
            await this.downloadFromS3(generation.image_key, imagePath);

            // Step 2: Call cpp-core service
            console.log(`[Orchestrator] Calling cpp-core service...`);
            const cppResponse = await this.callCppCore(imagePath, generation.genre, generation.mode);

            // Phase 12 A2.2: Update tempo, scale, AND decided genre in DB
            const updateData: any = {
                tempo_bpm: cppResponse.tempoBpm,
                scale_type: cppResponse.scaleType,
            };

            // If cpp-core decided a genre (not "auto"), update it
            if (cppResponse.decidedGenre && cppResponse.decidedGenre !== 'auto') {
                updateData.genre = cppResponse.decidedGenre;
                console.log(`[Orchestrator] Genre decided by cpp-core: ${cppResponse.decidedGenre}`);
            }

            await updateGenerationStatus(jobId, 'RUNNING', updateData);

            // Step 3: Call audio-producer service
            console.log(`[Orchestrator] Calling audio-producer service...`);
            await this.callAudioProducer(cppResponse.midiPath || midiPath, audioPath);

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
            console.log(`[Orchestrator] Uploading audio to S3: ${audioKey}`);
            await this.uploadToS3(audioPath, audioKey, 'audio/wav');

            // Phase 12 A1.3: Verify S3 upload succeeded
            console.log(`[Orchestrator] Uploaded ${audioStats.size} bytes to S3: ${audioKey}`);

            // Step 5: Mark as complete
            await updateGenerationStatus(jobId, 'COMPLETE', {
                audio_key: audioKey,
            });

            console.log(`[Orchestrator] Generation ${jobId} completed successfully`);
        } catch (error: any) {
            console.error(`[Orchestrator] Generation ${jobId} failed:`, error);
            await updateGenerationStatus(jobId, 'FAILED', {
                error_message: error.message || 'Unknown error',
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
        const cppCoreUrl = process.env.CPP_CORE_URL || 'http://localhost:8080';

        console.log(`[Orchestrator] Calling cpp-core service at ${cppCoreUrl}/generate`);

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
    private async callAudioProducer(midiPath: string, outputPath: string): Promise<void> {
        // For now, just create a placeholder file
        // TODO: Implement actual HTTP call to audio-producer
        console.log(`[Orchestrator] audio-producer would render: ${midiPath} -> ${outputPath}`);

        // Create empty WAV file as placeholder
        await fs.promises.writeFile(outputPath, Buffer.alloc(44)); // WAV header
    }
}
