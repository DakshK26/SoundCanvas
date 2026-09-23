// S3 access. The browser uploads images and downloads songs directly through
// short-lived presigned URLs; only the worker reads and writes bytes itself.
import { GetObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { requireEnv } from "../env";

const s3 = new S3Client({});
const BUCKET = requireEnv("S3_BUCKET");
const URL_EXPIRY_SECONDS = 15 * 60; // long enough to upload or play, short enough to not be shared

export const imageKey = (jobId: string) => `images/${jobId}`;
export const audioKey = (jobId: string) => `audio/${jobId}.wav`;

/** A URL the browser can PUT the image to. */
export function uploadUrl(key: string): Promise<string> {
  return getSignedUrl(s3, new PutObjectCommand({ Bucket: BUCKET, Key: key }), {
    expiresIn: URL_EXPIRY_SECONDS,
  });
}

/** A URL the browser can GET the file from. */
export function downloadUrl(key: string): Promise<string> {
  return getSignedUrl(s3, new GetObjectCommand({ Bucket: BUCKET, Key: key }), {
    expiresIn: URL_EXPIRY_SECONDS,
  });
}

export async function getObject(key: string): Promise<Buffer> {
  const object = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
  return Buffer.from(await object.Body!.transformToByteArray());
}

export async function putObject(key: string, body: Buffer, contentType: string): Promise<void> {
  await s3.send(new PutObjectCommand({ Bucket: BUCKET, Key: key, Body: body, ContentType: contentType }));
}
