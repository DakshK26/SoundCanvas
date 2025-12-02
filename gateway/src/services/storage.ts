import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

// ============================================================================
// Phase 10+: S3 Storage Service
// ============================================================================

const AWS_REGION = process.env.AWS_REGION || 'us-east-2';
const S3_BUCKET_NAME = process.env.S3_BUCKET_NAME || '';
const USE_S3 = process.env.USE_S3 === 'true';
const S3_ENDPOINT = process.env.S3_ENDPOINT; // Internal endpoint for MinIO
const S3_PUBLIC_ENDPOINT = process.env.S3_PUBLIC_ENDPOINT; // Public endpoint for presigned URLs

// Initialize S3 Client (credentials from environment variables)
let s3Client: S3Client | null = null;
let s3PublicClient: S3Client | null = null;

if (USE_S3) {
  // Internal client for direct operations
  s3Client = new S3Client({
    region: AWS_REGION,
    endpoint: S3_ENDPOINT,
    forcePathStyle: !!S3_ENDPOINT,
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
    },
  });

  // Public client for generating presigned URLs (uses public endpoint if available)
  const publicEndpoint = S3_PUBLIC_ENDPOINT || S3_ENDPOINT;
  s3PublicClient = new S3Client({
    region: AWS_REGION,
    endpoint: publicEndpoint,
    forcePathStyle: !!publicEndpoint,
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
    if (!USE_S3 || !s3PublicClient) {
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

    // URL expires in 1 hour - use public client for browser-accessible URLs
    return await getSignedUrl(s3PublicClient, command, { expiresIn: 3600 });
  }

  /**
   * Generate pre-signed S3 download URL for image
   */
  async getImageReadUrl(key: string): Promise<string> {
    if (!USE_S3 || !s3PublicClient) {
      throw new Error('S3 storage not configured');
    }

    const command = new GetObjectCommand({
      Bucket: S3_BUCKET_NAME,
      Key: key,
    });

    // URL expires in 1 hour - use public client for browser-accessible URLs
    return await getSignedUrl(s3PublicClient, command, { expiresIn: 3600 });
  }

  /**
   * Generate pre-signed S3 upload URL for audio
   */
  async getAudioUploadUrl(userId: string, jobId: string): Promise<string> {
    if (!USE_S3 || !s3PublicClient) {
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

    // Use public client for browser-accessible URLs
    return await getSignedUrl(s3PublicClient, command, { expiresIn: 3600 });
  }

  /**
   * Generate pre-signed S3 download URL for audio
   */
  async getAudioReadUrl(key: string): Promise<string> {
    if (!USE_S3 || !s3PublicClient) {
      throw new Error('S3 storage not configured');
    }

    const command = new GetObjectCommand({
      Bucket: S3_BUCKET_NAME,
      Key: key,
    });

    // Use public client for browser-accessible URLs
    return await getSignedUrl(s3PublicClient, command, { expiresIn: 3600 });
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
