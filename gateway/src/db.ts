// The `generations` table in RDS MySQL: one row per job, tracking its status.
// Image and audio files live in S3 under keys derived from the job id (see aws/s3.ts).
import mysql, { ResultSetHeader, RowDataPacket } from "mysql2/promise";
import { requireEnv } from "./env";

export type Status = "PENDING" | "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface Generation {
  id: string;
  status: Status;
  genre: string | null; // the user's pick, or the model's prediction once processed
  confidence: number | null; // the model's confidence; null when the user picked the genre
  error_message: string | null;
  created_at: Date;
}

const pool = mysql.createPool({
  host: requireEnv("DB_HOST"),
  user: requireEnv("DB_USER"),
  password: requireEnv("DB_PASSWORD"),
  database: requireEnv("DB_NAME"),
});

/** Creates the table on first start. */
export async function createTable(): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS generations (
      id            CHAR(36) PRIMARY KEY,
      status        ENUM('PENDING','QUEUED','PROCESSING','COMPLETED','FAILED') NOT NULL,
      genre         VARCHAR(20),
      confidence    FLOAT,
      error_message TEXT,
      created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )`);
}

/** Adds a new job waiting for its image upload. */
export async function insertGeneration(id: string, genre: string | null): Promise<void> {
  await pool.query("INSERT INTO generations (id, status, genre) VALUES (?, 'PENDING', ?)", [id, genre]);
}

/** Looks up one job. */
export async function getGeneration(id: string): Promise<Generation | null> {
  const [rows] = await pool.query<RowDataPacket[]>("SELECT * FROM generations WHERE id = ?", [id]);
  return (rows[0] as Generation) ?? null;
}

/** Moves a job from PENDING to QUEUED. Returns false if it was already started. */
export async function markQueued(id: string): Promise<boolean> {
  const [result] = await pool.query<ResultSetHeader>(
    "UPDATE generations SET status = 'QUEUED' WHERE id = ? AND status = 'PENDING'", [id]);
  return result.affectedRows === 1;
}

export async function markProcessing(id: string): Promise<void> {
  await pool.query("UPDATE generations SET status = 'PROCESSING' WHERE id = ?", [id]);
}

export async function markCompleted(id: string, genre: string, confidence: number | null): Promise<void> {
  await pool.query(
    "UPDATE generations SET status = 'COMPLETED', genre = ?, confidence = ? WHERE id = ?",
    [genre, confidence, id]);
}

export async function markFailed(id: string, message: string): Promise<void> {
  await pool.query(
    "UPDATE generations SET status = 'FAILED', error_message = ? WHERE id = ?", [message, id]);
}
