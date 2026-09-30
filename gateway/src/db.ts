// Every MySQL query the API and the worker run. Status changes are compare-and-set: each UPDATE
// names the status it expects to move from, and the caller checks that exactly one row changed.
// That is what makes double clicks and duplicate SQS deliveries harmless.
import mysql, { ResultSetHeader, RowDataPacket } from "mysql2/promise";
import { requireEnv } from "./env";

export type Status = "PENDING" | "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
export type Feedback = "UP" | "DOWN";

export interface Generation {
  id: string;
  client_id: string;
  status: Status;
  requested_genre: string | null;
  genre: string | null;
  confidence: number | null;
  features: number[] | null;
  feedback: Feedback | null;
  error_message: string | null;
  created_at: Date;
}

// db.t4g.micro allows about 60 connections; 1 API task and up to 5 workers at 5 each is 30.
const CONNECTIONS_PER_TASK = 5;

// The sweeper fails jobs stuck in QUEUED or PROCESSING for longer than this.
const STALE_JOB_MINUTES = 60;

// Must match the S3 lifecycle rule in storage.tf.
const FILE_RETENTION_DAYS = 30;

export const pool = mysql.createPool({
  host: requireEnv("DB_HOST"),
  user: requireEnv("DB_USER"),
  password: requireEnv("DB_PASSWORD"),
  database: requireEnv("DB_NAME"),
  connectionLimit: CONNECTIONS_PER_TASK,
});

// createGeneration writes the PENDING row before it counts, so the rate limit can never be exceeded.
export async function insertGeneration(row: {
  id: string; clientId: string; clientIp: string; requestedGenre: string | null;
}): Promise<void> {
  await pool.query(
    "INSERT INTO generations (id, client_id, client_ip, status, requested_genre) VALUES (?, ?, ?, 'PENDING', ?)",
    [row.id, row.clientId, row.clientIp, row.requestedGenre]);
}

// Used when the new row itself pushed this browser or IP over the hourly limit.
export async function deleteGeneration(id: string): Promise<void> {
  await pool.query("DELETE FROM generations WHERE id = ?", [id]);
}

// Looked up by job id. The caller still has to check client_id; this does not.
export async function getGeneration(id: string): Promise<Generation | null> {
  const [rows] = await pool.query<RowDataPacket[]>("SELECT * FROM generations WHERE id = ?", [id]);
  return (rows[0] as Generation) ?? null;
}

// History: this browser's started jobs from the last 30 days, newest first. Uses history_lookup.
export async function listGenerations(clientId: string, limit: number): Promise<Generation[]> {
  const [rows] = await pool.query<RowDataPacket[]>(
    `SELECT * FROM generations
     WHERE client_id = ? AND status <> 'PENDING' AND created_at > NOW() - INTERVAL ? DAY
     ORDER BY created_at DESC LIMIT ?`, [clientId, FILE_RETENTION_DAYS, limit]);
  return rows as Generation[];
}

// Rate limit: songs in the last hour from this browser or this IP, so clearing localStorage
// doesn't reset it. The OR is why there is an index on each column.
export async function countRecentGenerations(clientId: string, clientIp: string): Promise<number> {
  const [rows] = await pool.query<RowDataPacket[]>(
    `SELECT COUNT(*) AS count FROM generations
     WHERE (client_id = ? OR client_ip = ?) AND created_at > NOW() - INTERVAL 1 HOUR`,
    [clientId, clientIp]);
  return rows[0].count;
}

// PENDING to QUEUED. False means startGeneration was already called for this job.
export async function markQueued(id: string): Promise<boolean> {
  return update("UPDATE generations SET status = 'QUEUED' WHERE id = ? AND status = 'PENDING'", [id]);
}

// Undoes markQueued when the SQS send fails.
export async function markPending(id: string): Promise<void> {
  await update("UPDATE generations SET status = 'PENDING' WHERE id = ? AND status = 'QUEUED'", [id]);
}

// PROCESSING is allowed too, because a retry picks the job up in that state.
export async function startProcessing(id: string): Promise<boolean> {
  return update(
    "UPDATE generations SET status = 'PROCESSING' WHERE id = ? AND status IN ('QUEUED', 'PROCESSING')", [id]);
}

// Saves the genre, the model's confidence and the 8 features with the finished song.
export async function markCompleted(
  id: string, genre: string, confidence: number | null, features: number[],
): Promise<void> {
  await update(
    `UPDATE generations SET status = 'COMPLETED', genre = ?, confidence = ?, features = ?
     WHERE id = ? AND status = 'PROCESSING'`,
    [genre, confidence, JSON.stringify(features), id]);
}

// Permanent failures and the last retry both land here; the message is what the browser shows.
export async function markFailed(id: string, message: string): Promise<void> {
  await update(
    "UPDATE generations SET status = 'FAILED', error_message = ? WHERE id = ? AND status IN ('QUEUED', 'PROCESSING')",
    [message, id]);
}

// A worker that crashes on the last attempt never marks its job failed; SQS just moves it to the DLQ.
export async function failStaleJobs(): Promise<number> {
  const [result] = await pool.query<ResultSetHeader>(
    `UPDATE generations SET status = 'FAILED', error_message = 'Timed out'
     WHERE status IN ('QUEUED', 'PROCESSING') AND updated_at < NOW() - INTERVAL ? MINUTE`,
    [STALE_JOB_MINUTES]);
  return result.affectedRows;
}

// Only a COMPLETED row owned by this client id can be rated.
export async function setFeedback(id: string, clientId: string, feedback: Feedback): Promise<boolean> {
  return update(
    "UPDATE generations SET feedback = ? WHERE id = ? AND client_id = ? AND status = 'COMPLETED'",
    [feedback, id, clientId]);
}

// True if exactly one row changed, meaning the status the query expected was really there.
async function update(sql: string, params: unknown[]): Promise<boolean> {
  const [result] = await pool.query<ResultSetHeader>(sql, params);
  return result.affectedRows === 1;
}
