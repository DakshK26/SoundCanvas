import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

// ============================================================================
// Phase 10+: S3 Storage Service
// ============================================================================

const AWS_REGION = process.env.AWS_REGION || 'us-east-2';
const S3_BUCKET_NAME = process.env.S3_BUCKET_NAME || '';
const USE_S3 = process.env.USE_S3 === 'true';

// Initialize S3 Client (credentials from environment variables)
let s3Client: S3Client | null = null;

if (USE_S3) {
  s3Client = new S3Client({
    region: AWS_REGION,
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
    },
  });
}

export class StorageService {
  /**
   * Generate pre-signed S3 upload URL for image
   * Frontend will PUT the image file directly to this URL
   */
  async getImageUploadUrl(userId: string, jobId: string): Promise<string> {
    if (!USE_S3 || !s3Client) {
      throw new Error('S3 storage not configured');
    }

    const key = `images/${userId}/${jobId}/input.jpg`;
    const command = new PutObjectCommand({
      Bucket: S3_BUCKET_NAME,
      Key: key,
      ContentType: 'image/jpeg',
      CacheControl: 'max-age=31536000',
      Metadata: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, HEAD',
      },
    });

    // URL expires in 1 hour
    return await getSignedUrl(s3Client, command, { expiresIn: 3600 });
  }

  /**
   * Generate pre-signed S3 download URL for image
   */
  async getImageReadUrl(key: string): Promise<string> {
    if (!USE_S3 || !s3Client) {
      throw new Error('S3 storage not configured');
    }

    const command = new GetObjectCommand({
      Bucket: S3_BUCKET_NAME,
      Key: key,
    });

    // URL expires in 1 hour
    return await getSignedUrl(s3Client, command, { expiresIn: 3600 });
  }

  /**
   * Generate pre-signed S3 upload URL for audio
   */
  async getAudioUploadUrl(userId: string, jobId: string): Promise<string> {
    if (!USE_S3 || !s3Client) {
      throw new Error('S3 storage not configured');
    }

    const key = `audio/${userId}/${jobId}/output.wav`;
    const command = new PutObjectCommand({
      Bucket: S3_BUCKET_NAME,
      Key: key,
      ContentType: 'audio/wav',
      CacheControl: 'max-age=31536000',
      Metadata: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, HEAD',
      },
    });

    return await getSignedUrl(s3Client, command, { expiresIn: 3600 });
  }

  /**
   * Generate pre-signed S3 download URL for audio
   */
  async getAudioReadUrl(key: string): Promise<string> {
    if (!USE_S3 || !s3Client) {
      throw new Error('S3 storage not configured');
    }

    const command = new GetObjectCommand({
      Bucket: S3_BUCKET_NAME,
      Key: key,
    });

    return await getSignedUrl(s3Client, command, { expiresIn: 3600 });
  }

  /**
   * Get S3 key from image upload URL
   */
  getImageKeyFromUploadUrl(uploadUrl: string): string {
    const url = new URL(uploadUrl);
    return url.pathname.substring(1); // Remove leading '/'
  }

  /**
   * Get S3 key for audio output
   */
  getAudioKey(userId: string, jobId: string): string {
    return `audio/${userId}/${jobId}/output.wav`;
  }

  /**
   * Get S3 key for image input
   */
  getImageKey(userId: string, jobId: string): string {
    return `images/${userId}/${jobId}/input.jpg`;
  }
}
