// Queries on the `generations` table in RDS MySQL: one row per song request.
// The schema lives in migrations/ (applied by migrate.ts before each deploy).
//
// Why a relational database: the app needs a browser's history in time order,
// counts of recent requests for rate limiting, status changes that only apply
// from the right previous status, and a record of features, predictions and
// feedback to retrain the model on. All of these are simple SQL.
// Image and audio files live in S3 under keys derived from the job id (see aws/s3.ts).
import mysql, { ResultSetHeader, RowDataPacket } from "mysql2/promise";
import { requireEnv } from "./env";

export type Status = "PENDING" | "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
export type Feedback = "UP" | "DOWN";

export interface Generation {
  id: string;
  client_id: string; // anonymous id the browser generates and keeps in localStorage
  status: Status;
  requested_genre: string | null; // the user's pick; null lets the model choose
  genre: string | null; // the genre actually used, set when the song is done
  confidence: number | null; // the model's confidence; null when the user picked
  features: number[] | null; // the image's 8 features, kept for retraining
  feedback: Feedback | null; // the user's thumbs up or down
  error_message: string | null;
  created_at: Date;
}

// db.t4g.micro allows about 60 connections. At full scale (5 API + 5 worker tasks)
// 5 each is 50, leaving room for migrations and a person debugging.
const CONNECTIONS_PER_TASK = 5;

// How long a job may sit in QUEUED or PROCESSING before it is declared lost.
// A job normally takes about a minute; even a busy browser's backlog clears well within this.
const STALE_JOB_MINUTES = 60;

// S3 deletes images and songs after this many days (the lifecycle rule in infra/terraform/storage.tf).
const FILE_RETENTION_DAYS = 30;

export const pool = mysql.createPool({
  host: requireEnv("DB_HOST"),
  user: requireEnv("DB_USER"),
  password: requireEnv("DB_PASSWORD"),
  database: requireEnv("DB_NAME"),
  connectionLimit: CONNECTIONS_PER_TASK,
});

export async function insertGeneration(row: {
  id: string; clientId: string; clientIp: string; requestedGenre: string | null;
}): Promise<void> {
  await pool.query(
    "INSERT INTO generations (id, client_id, client_ip, status, requested_genre) VALUES (?, ?, ?, 'PENDING', ?)",
    [row.id, row.clientId, row.clientIp, row.requestedGenre]);
}

export async function deleteGeneration(id: string): Promise<void> {
  await pool.query("DELETE FROM generations WHERE id = ?", [id]);
}

export async function getGeneration(id: string): Promise<Generation | null> {
  const [rows] = await pool.query<RowDataPacket[]>("SELECT * FROM generations WHERE id = ?", [id]);
  return (rows[0] as Generation) ?? null;
}

/** One browser's songs, newest first. PENDING jobs are skipped: their image was never uploaded.
 *  Older songs are skipped too: S3 has deleted their files. */
export async function listGenerations(clientId: string, limit: number): Promise<Generation[]> {
  const [rows] = await pool.query<RowDataPacket[]>(
    `SELECT * FROM generations
     WHERE client_id = ? AND status <> 'PENDING' AND created_at > NOW() - INTERVAL ? DAY
     ORDER BY created_at DESC LIMIT ?`, [clientId, FILE_RETENTION_DAYS, limit]);
  return rows as Generation[];
}

/** How many songs this browser or IP address requested in the last hour. */
export async function countRecentGenerations(clientId: string, clientIp: string): Promise<number> {
  const [rows] = await pool.query<RowDataPacket[]>(
    `SELECT COUNT(*) AS count FROM generations
     WHERE (client_id = ? OR client_ip = ?) AND created_at > NOW() - INTERVAL 1 HOUR`,
    [clientId, clientIp]);
  return rows[0].count;
}

// Status changes. Each UPDATE only applies from the expected previous status and
// reports whether it did, so a repeated or out-of-order call changes nothing.

/** PENDING -> QUEUED. False if the job was already started. */
export async function markQueued(id: string): Promise<boolean> {
  return update("UPDATE generations SET status = 'QUEUED' WHERE id = ? AND status = 'PENDING'", [id]);
}

/** QUEUED -> PENDING, undoing markQueued when sending to SQS fails, so the user can retry. */
export async function markPending(id: string): Promise<void> {
  await update("UPDATE generations SET status = 'PENDING' WHERE id = ? AND status = 'QUEUED'", [id]);
}

/** QUEUED -> PROCESSING. PROCESSING is accepted too, for a retry after a failed attempt.
 *  False if the job already finished, which happens when SQS delivers a message twice. */
export async function startProcessing(id: string): Promise<boolean> {
  return update(
    "UPDATE generations SET status = 'PROCESSING' WHERE id = ? AND status IN ('QUEUED', 'PROCESSING')", [id]);
}

export async function markCompleted(
  id: string, genre: string, confidence: number | null, features: number[],
): Promise<void> {
  await update(
    `UPDATE generations SET status = 'COMPLETED', genre = ?, confidence = ?, features = ?
     WHERE id = ? AND status = 'PROCESSING'`,
    [genre, confidence, JSON.stringify(features), id]);
}

export async function markFailed(id: string, message: string): Promise<void> {
  await update(
    "UPDATE generations SET status = 'FAILED', error_message = ? WHERE id = ? AND status IN ('QUEUED', 'PROCESSING')",
    [message, id]);
}

/**
 * Fails jobs stuck in QUEUED or PROCESSING, and returns how many. This catches the one
 * path the worker cannot: a worker that crashes on the final attempt never marks the job,
 * and SQS moves the message to the dead-letter queue on its next receive.
 */
export async function failStaleJobs(): Promise<number> {
  const [result] = await pool.query<ResultSetHeader>(
    `UPDATE generations SET status = 'FAILED', error_message = 'Timed out'
     WHERE status IN ('QUEUED', 'PROCESSING') AND updated_at < NOW() - INTERVAL ? MINUTE`,
    [STALE_JOB_MINUTES]);
  return result.affectedRows;
}

/** Records a thumbs up or down on a finished song. False if it isn't this browser's finished song. */
export async function setFeedback(id: string, clientId: string, feedback: Feedback): Promise<boolean> {
  return update(
    "UPDATE generations SET feedback = ? WHERE id = ? AND client_id = ? AND status = 'COMPLETED'",
    [feedback, id, clientId]);
}

async function update(sql: string, params: unknown[]): Promise<boolean> {
  const [result] = await pool.query<ResultSetHeader>(sql, params);
  return result.affectedRows === 1;
}
