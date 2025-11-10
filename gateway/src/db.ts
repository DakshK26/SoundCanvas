import mysql from "mysql2/promise";

let pool: mysql.Pool;

export async function initDb() {
  pool = mysql.createPool({
    host: process.env.DB_HOST || "localhost",
    port: Number(process.env.DB_PORT || "3306"),
    user: process.env.DB_USER || "soundcanvas",
    password: process.env.DB_PASSWORD || "soundcanvas",
    database: process.env.DB_NAME || "soundcanvas",
    connectionLimit: 10,
  });

  await createTables();
}

async function createTables() {
  // Simple auto-migration for Phase 5
  await pool.query(`
    CREATE TABLE IF NOT EXISTS sound_generations (
      id INT AUTO_INCREMENT PRIMARY KEY,
      image_path VARCHAR(255) NOT NULL,
      audio_path VARCHAR(255) NOT NULL,
      mode ENUM('heuristic','model') NOT NULL,
      tempo_bpm FLOAT NOT NULL,
      base_frequency FLOAT NOT NULL,
      brightness FLOAT NOT NULL,
      volume FLOAT NOT NULL,
      duration_seconds FLOAT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
  `);
}

export type DbSoundGeneration = {
  id: number;
  imagePath: string;
  audioPath: string;
  mode: "heuristic" | "model";
  params: {
    tempoBpm: number;
    baseFrequency: number;
    brightness: number;
    volume: number;
    durationSeconds: number;
  };
  createdAt: string;
};

// Insert a new record
export async function dbInsertSoundGeneration(input: {
  imagePath: string;
  audioPath: string;
  mode: "heuristic" | "model";
  params: {
    tempoBpm: number;
    baseFrequency: number;
    brightness: number;
    volume: number;
    durationSeconds: number;
  };
}): Promise<DbSoundGeneration> {
  const [result] = await pool.execute<mysql.ResultSetHeader>(
    `
    INSERT INTO sound_generations
      (image_path, audio_path, mode, tempo_bpm, base_frequency, brightness, volume, duration_seconds)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `,
    [
      input.imagePath,
      input.audioPath,
      input.mode,
      input.params.tempoBpm,
      input.params.baseFrequency,
      input.params.brightness,
      input.params.volume,
      input.params.durationSeconds,
    ]
  );

  const insertedId = result.insertId;

  const [rows] = await pool.execute<any[]>(
    `SELECT * FROM sound_generations WHERE id = ?`,
    [insertedId]
  );

  const row = rows[0];
  return mapRow(row);
}

// History query
export async function dbGetHistory(limit: number): Promise<DbSoundGeneration[]> {
  const [rows] = await pool.execute<any[]>(
    `
    SELECT * FROM sound_generations
    ORDER BY created_at DESC
    LIMIT ?
    `,
    [limit]
  );
  return rows.map(mapRow);
}

function mapRow(row: any): DbSoundGeneration {
  return {
    id: row.id,
    imagePath: row.image_path,
    audioPath: row.audio_path,
    mode: row.mode,
    params: {
      tempoBpm: row.tempo_bpm,
      baseFrequency: row.base_frequency,
      brightness: row.brightness,
      volume: row.volume,
      durationSeconds: row.duration_seconds,
    },
    createdAt: row.created_at.toISOString
      ? row.created_at.toISOString()
      : String(row.created_at),
  };
}