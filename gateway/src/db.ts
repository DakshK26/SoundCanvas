import mysql from "mysql2/promise";

let pool: mysql.Pool;

export async function initDb() {
  // Support both RDS and local MySQL
  const isRDS = process.env.RDS_ENDPOINT !== undefined;

  if (isRDS) {
    // AWS RDS configuration
    const [host, portStr] = process.env.RDS_ENDPOINT!.split(':');
    const port = portStr ? parseInt(portStr) : 3306;

    pool = mysql.createPool({
      host: host,
      port: port,
      user: process.env.RDS_USERNAME || 'admin',
      password: process.env.RDS_PASSWORD,
      database: process.env.RDS_DB_NAME || 'soundcanvas',
      connectionLimit: 10,
      ssl: process.env.RDS_SSL === 'true' ? { rejectUnauthorized: false } : undefined,
    });

    console.log(`✓ Connected to RDS MySQL: ${host}:${port}`);
  } else {
    // Local MySQL configuration (backwards compatible)
    pool = mysql.createPool({
      host: process.env.DB_HOST || "localhost",
      port: Number(process.env.DB_PORT || "3306"),
      user: process.env.DB_USER || "soundcanvas",
      password: process.env.DB_PASSWORD || "soundcanvas",
      database: process.env.DB_NAME || "soundcanvas",
      connectionLimit: 10,
    });

    console.log(`✓ Connected to local MySQL: ${process.env.DB_HOST || 'localhost'}`);
  }

  await createTables();
}

async function createTables() {
  // Phase 5: Legacy table for backwards compatibility
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

  // Phase 10: New generations table for S3-based workflow
  await pool.query(`
    CREATE TABLE IF NOT EXISTS generations (
      id VARCHAR(36) PRIMARY KEY,
      user_id VARCHAR(255) DEFAULT 'default-user',
      image_key VARCHAR(512) NOT NULL,
      audio_key VARCHAR(512),
      genre VARCHAR(50) NOT NULL,
      tempo_bpm FLOAT DEFAULT 0,
      mood FLOAT DEFAULT 0.5,
      scale_type VARCHAR(50),
      status ENUM('PENDING','RUNNING','COMPLETE','FAILED') NOT NULL DEFAULT 'PENDING',
      mode ENUM('heuristic','model') NOT NULL DEFAULT 'model',
      error_message TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      
      INDEX idx_user_created (user_id, created_at DESC),
      INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
  `);

  console.log('✓ Database tables created/verified');
}

// ============================================================================
// Phase 10: Generations CRUD
// ============================================================================

export interface Generation {
  id: string;
  user_id: string;
  image_key: string;
  audio_key: string | null;
  genre: string;
  tempo_bpm: number;
  mood: number;
  scale_type: string | null;
  status: 'PENDING' | 'RUNNING' | 'COMPLETE' | 'FAILED';
  mode: 'heuristic' | 'model';
  error_message: string | null;
  created_at: Date;
  updated_at: Date;
}

export async function insertGeneration(gen: {
  id: string;
  user_id: string;
  image_key: string;
  genre: string;
  tempo_bpm?: number;
  mood?: number;
  scale_type?: string;
  mode?: 'heuristic' | 'model';
}): Promise<void> {
  await pool.query(
    `INSERT INTO generations (id, user_id, image_key, genre, tempo_bpm, mood, scale_type, mode, status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')`,
    [
      gen.id,
      gen.user_id,
      gen.image_key,
      gen.genre,
      gen.tempo_bpm || 0,
      gen.mood || 0.5,
      gen.scale_type || null,
      gen.mode || 'model',
    ]
  );
}

export async function getGenerationById(id: string): Promise<Generation | null> {
  const [rows] = await pool.query<any[]>(
    'SELECT * FROM generations WHERE id = ?',
    [id]
  );
  return rows.length > 0 ? rows[0] : null;
}

export async function getUserGenerations(userId: string, limit = 20): Promise<Generation[]> {
  const [rows] = await pool.query<any[]>(
    `SELECT * FROM generations 
     WHERE user_id = ? 
     ORDER BY created_at DESC 
     LIMIT ?`,
    [userId, limit]
  );
  return rows;
}

export async function updateGenerationStatus(
  id: string,
  status: 'PENDING' | 'RUNNING' | 'COMPLETE' | 'FAILED',
  updates?: {
    audio_key?: string;
    error_message?: string;
    tempo_bpm?: number;
    scale_type?: string;
  }
): Promise<void> {
  const params: any[] = [status];
  let sql = 'UPDATE generations SET status = ?';

  if (updates?.audio_key) {
    sql += ', audio_key = ?';
    params.push(updates.audio_key);
  }
  if (updates?.error_message !== undefined) {
    sql += ', error_message = ?';
    params.push(updates.error_message);
  }
  if (updates?.tempo_bpm) {
    sql += ', tempo_bpm = ?';
    params.push(updates.tempo_bpm);
  }
  if (updates?.scale_type) {
    sql += ', scale_type = ?';
    params.push(updates.scale_type);
  }

  sql += ' WHERE id = ?';
  params.push(id);

  await pool.query(sql, params);
}

// ============================================================================
// Phase 5: Legacy SoundGeneration CRUD (backwards compatible)
// ============================================================================

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
