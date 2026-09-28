// all the SQL. one table, `generations`, one row per song (schema's in migrations/)
//
// why mysql and not dynamo: I need history sorted by time, a "how many in the last hour
// by clientId OR ip" count, updates that only apply from the right status, and I want to
// query features vs thumbs up/down later for retraining. all trivial in SQL, annoying in dynamo.
// the actual files are in S3, keyed by job id (aws/s3.ts)
import mysql, { ResultSetHeader, RowDataPacket } from "mysql2/promise";
import { requireEnv } from "./env";

export type Status = "PENDING" | "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
export type Feedback = "UP" | "DOWN";

export interface Generation {
  id: string;
  client_id: string; // random uuid from the browser's localStorage (not a login)
  status: Status;
  requested_genre: string | null; // null = let the model pick
  genre: string | null; // what actually got used, set at the end
  confidence: number | null; // null when the user picked
  features: number[] | null; // saved for retraining later
  feedback: Feedback | null; // thumbs up/down
  error_message: string | null;
  created_at: Date;
}

// db.t4g.micro max_connections is ~60. 1 api + up to 5 workers * 5 = 30, leaves room
// for the migrate task + me poking at it. (if workers ever go way past 5 -> lower this or RDS Proxy)
const CONNECTIONS_PER_TASK = 5;

// a job takes ~1 min. if it's been QUEUED/PROCESSING for an hour something lost it
const STALE_JOB_MINUTES = 60;

// matches the S3 lifecycle rule in storage.tf - no point listing songs whose files are gone
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

// history. skip PENDING (never got an upload) and anything older than the S3 lifecycle
export async function listGenerations(clientId: string, limit: number): Promise<Generation[]> {
  const [rows] = await pool.query<RowDataPacket[]>(
    `SELECT * FROM generations
     WHERE client_id = ? AND status <> 'PENDING' AND created_at > NOW() - INTERVAL ? DAY
     ORDER BY created_at DESC LIMIT ?`, [clientId, FILE_RETENTION_DAYS, limit]);
  return rows as Generation[];
}

// rate limit count. OR on ip so clearing localStorage doesn't reset your limit
export async function countRecentGenerations(clientId: string, clientIp: string): Promise<number> {
  const [rows] = await pool.query<RowDataPacket[]>(
    `SELECT COUNT(*) AS count FROM generations
     WHERE (client_id = ? OR client_ip = ?) AND created_at > NOW() - INTERVAL 1 HOUR`,
    [clientId, clientIp]);
  return rows[0].count;
}

// --- status changes ---
// every UPDATE has "AND status = <what it should be now>" and returns whether a row changed.
// basically compare-and-set -> retries / duplicate deliveries can't mess up the state

// PENDING -> QUEUED. false = already started
export async function markQueued(id: string): Promise<boolean> {
  return update("UPDATE generations SET status = 'QUEUED' WHERE id = ? AND status = 'PENDING'", [id]);
}

// undo for markQueued when the SQS send fails, so they can hit start again
export async function markPending(id: string): Promise<void> {
  await update("UPDATE generations SET status = 'PENDING' WHERE id = ? AND status = 'QUEUED'", [id]);
}

// QUEUED -> PROCESSING. also allows PROCESSING -> PROCESSING bc a retry starts from there.
// false = already COMPLETED/FAILED (duplicate delivery)
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

// sweeper. the one case the worker can't handle itself: it crashes on the LAST attempt ->
// nobody marks the job failed, SQS just quietly moves the msg to the DLQ. this catches those
// so the user isn't stuck on "creating your track..." forever
export async function failStaleJobs(): Promise<number> {
  const [result] = await pool.query<ResultSetHeader>(
    `UPDATE generations SET status = 'FAILED', error_message = 'Timed out'
     WHERE status IN ('QUEUED', 'PROCESSING') AND updated_at < NOW() - INTERVAL ? MINUTE`,
    [STALE_JOB_MINUTES]);
  return result.affectedRows;
}

// client_id in the WHERE so you can only rate your own songs
export async function setFeedback(id: string, clientId: string, feedback: Feedback): Promise<boolean> {
  return update(
    "UPDATE generations SET feedback = ? WHERE id = ? AND client_id = ? AND status = 'COMPLETED'",
    [feedback, id, clientId]);
}

async function update(sql: string, params: unknown[]): Promise<boolean> {
  const [result] = await pool.query<ResultSetHeader>(sql, params);
  return result.affectedRows === 1;
}
