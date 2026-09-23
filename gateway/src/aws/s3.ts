// S3 access. The browser uploads images and downloads songs directly with
// short-lived presigned links, so large files never pass through the API.
import { GetObjectCommand, HeadObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { createPresignedPost } from "@aws-sdk/s3-presigned-post";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { requireEnv } from "../env";

const s3 = new S3Client({});
const BUCKET = requireEnv("S3_BUCKET");
const URL_EXPIRY_SECONDS = 15 * 60; // long enough to upload or play, short enough to not be shared
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10 MB covers any normal photo

export const imageKey = (jobId: string) => `images/${jobId}`;
export const audioKey = (jobId: string) => `audio/${jobId}.wav`;

export interface UploadForm {
  url: string;
  fields: Record<string, string>; // form fields the browser sends along with the file
}

/**
 * A presigned POST form for uploading the image. S3 itself enforces the
 * conditions: the file must be 10 MB or less and have the declared content type.
 */
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

/** A link the browser can GET the file from. */
export function downloadUrl(key: string): Promise<string> {
  return getSignedUrl(s3, new GetObjectCommand({ Bucket: BUCKET, Key: key }), {
    expiresIn: URL_EXPIRY_SECONDS,
  });
}

/** Whether the file exists, used to check the image was uploaded before queueing the job. */
export async function objectExists(key: string): Promise<boolean> {
  try {
    await s3.send(new HeadObjectCommand({ Bucket: BUCKET, Key: key }));
    return true;
  } catch (error) {
    if ((error as Error).name === "NotFound") return false;
    throw error;
  }
}

export async function getObject(key: string): Promise<Buffer> {
  const object = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
  return Buffer.from(await object.Body!.transformToByteArray());
}

export async function putObject(key: string, body: Buffer, contentType: string): Promise<void> {
  await s3.send(new PutObjectCommand({ Bucket: BUCKET, Key: key, Body: body, ContentType: contentType }));
}
