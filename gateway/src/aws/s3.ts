// S3 stuff. browser talks to S3 directly w/ presigned links so images/wavs never
// go thru the API (that's why express.json can be capped at 10kb)
import { GetObjectCommand, HeadObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { createPresignedPost } from "@aws-sdk/s3-presigned-post";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { requireEnv } from "../env";

const s3 = new S3Client({});
const BUCKET = requireEnv("S3_BUCKET");
const URL_EXPIRY_SECONDS = 15 * 60; // 15 min: enough to upload/play, not great for passing links around
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10MB, a phone photo is ~2-5MB

export const imageKey = (jobId: string) => `images/${jobId}`;
export const audioKey = (jobId: string) => `audio/${jobId}.wav`;

export interface UploadForm {
  url: string;
  fields: Record<string, string>; // browser sends these + the file (file has to be LAST or S3 rejects it)
}

// presigned POST instead of presigned PUT bc POST policies can have conditions -> S3 itself
// enforces the size limit + content type. a PUT url can't cap the size.
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

// new link every time a row is returned, so history keeps working after the old ones expire
export function downloadUrl(key: string): Promise<string> {
  return getSignedUrl(s3, new GetObjectCommand({ Bucket: BUCKET, Key: key }), {
    expiresIn: URL_EXPIRY_SECONDS,
  });
}

// HEAD request = cheap existence check. used before queueing so we don't run a job w/ no image
// gotcha: it throws "NotFound" (not NoSuchKey like GetObject does)
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
