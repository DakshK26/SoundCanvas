// S3 holds the uploaded images and the finished WAVs. Browsers upload and download with presigned
// links, so file bytes never go through the API; only the worker reads and writes objects itself.
import { GetObjectCommand, HeadObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { createPresignedPost } from "@aws-sdk/s3-presigned-post";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { requireEnv } from "../env";

// Credentials come from the ECS task role; locally, AWS_ENDPOINT_URL points the SDK at LocalStack.
const s3 = new S3Client({});
const BUCKET = requireEnv("S3_BUCKET");
const URL_EXPIRY_SECONDS = 15 * 60;
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

export const imageKey = (jobId: string) => `images/${jobId}`;
export const audioKey = (jobId: string) => `audio/${jobId}.wav`;

export interface UploadForm {
  url: string;
  // S3 rejects the form unless the file comes after these fields.
  fields: Record<string, string>;
}

// The policy is signed into the form, so S3 itself refuses a different key, a different content
// type, or a file outside 1 byte to 10 MB.
export function uploadForm(key: string, contentType: string): Promise<UploadForm> {
  return createPresignedPost(s3, {
    Bucket: BUCKET,
    Key: key,
    Conditions: [
      ["content-length-range", 1, MAX_UPLOAD_BYTES],
      ["eq", "$Content-Type", contentType],
    ],
    Fields: { "Content-Type": contentType },
    Expires: URL_EXPIRY_SECONDS,
  });
}

export function downloadUrl(key: string): Promise<string> {
  return getSignedUrl(s3, new GetObjectCommand({ Bucket: BUCKET, Key: key }), {
    expiresIn: URL_EXPIRY_SECONDS,
  });
}

// startGeneration uses this to make sure the browser really uploaded the image.
export async function objectExists(key: string): Promise<boolean> {
  try {
    await s3.send(new HeadObjectCommand({ Bucket: BUCKET, Key: key }));
    return true;
  } catch (error) {
    // HeadObject throws NotFound, not NoSuchKey like GetObject.
    if ((error as Error).name === "NotFound") return false;
    throw error;
  }
}

// The worker reads the image and writes the WAV with these two.
export async function getObject(key: string): Promise<Buffer> {
  const object = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
  return Buffer.from(await object.Body!.transformToByteArray());
}

export async function putObject(key: string, body: Buffer, contentType: string): Promise<void> {
  await s3.send(new PutObjectCommand({ Bucket: BUCKET, Key: key, Body: body, ContentType: contentType }));
}
