import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

// ============================================================================
// Phase 10+: S3 Storage Service
// ============================================================================

const AWS_REGION = process.env.AWS_REGION || 'us-east-2';
const S3_BUCKET_NAME = process.env.S3_BUCKET_NAME || '';
const USE_S3 = process.env.USE_S3 === 'true';
const S3_ENDPOINT = process.env.S3_ENDPOINT; // Internal endpoint for MinIO
const GATEWAY_PUBLIC_URL = process.env.GATEWAY_PUBLIC_URL || ''; // Public gateway URL for uploads

// Initialize S3 Client (credentials from environment variables)
let s3Client: S3Client | null = null;

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
}

export class StorageService {
  /**
   * Generate direct upload URL for image
   * Uses gateway's /upload endpoint instead of presigned S3 URLs
   */
  async getImageUploadUrl(userId: string, jobId: string): Promise<string> {
    if (!USE_S3) {
      throw new Error('S3 storage not configured');
    }

    const key = `images/${userId}/${jobId}/input.jpg`;

    // Return direct upload URL through gateway
    return `${GATEWAY_PUBLIC_URL}/upload/${key}`;
  }

  /**
   * Generate direct download URL for image
   */
  async getImageReadUrl(key: string): Promise<string> {
    if (!USE_S3) {
      throw new Error('S3 storage not configured');
    }

    // Return direct download URL through gateway
    return `${GATEWAY_PUBLIC_URL}/files/${key}`;
  }

  /**
   * Generate direct upload URL for audio
   */
  async getAudioUploadUrl(userId: string, jobId: string): Promise<string> {
    if (!USE_S3) {
      throw new Error('S3 storage not configured');
    }

    const key = `audio/${userId}/${jobId}/output.wav`;

    // Return direct upload URL through gateway
    return `${GATEWAY_PUBLIC_URL}/upload/${key}`;
  }

  /**
   * Generate direct download URL for audio
   */
  async getAudioReadUrl(key: string): Promise<string> {
    if (!USE_S3) {
      throw new Error('S3 storage not configured');
    }

    // Return direct download URL through gateway
    return `${GATEWAY_PUBLIC_URL}/files/${key}`;
  }

  /**
   * Get S3 key from image upload URL
   */
  getImageKeyFromUploadUrl(uploadUrl: string): string {
    const url = new URL(uploadUrl);
    // Remove /upload/ prefix
    return url.pathname.replace(/^\/upload\//, '');
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
