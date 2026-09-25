// Applies the SQL files in migrations/ that have not run yet, in filename order,
// and records each one in schema_migrations. Run once per deploy, before the new
// API and worker start (a one-off ECS task in .github/workflows/deploy.yml).
import { readdir, readFile } from "fs/promises";
import path from "path";
import { RowDataPacket } from "mysql2/promise";
import { pool } from "./db";

const MIGRATIONS_DIR = path.join(__dirname, "..", "migrations");

async function migrate(): Promise<void> {
  await pool.query(`CREATE TABLE IF NOT EXISTS schema_migrations (
    name VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)`);
  const [rows] = await pool.query<RowDataPacket[]>("SELECT name FROM schema_migrations");
  const applied = new Set(rows.map((row) => row.name as string));

  const files = (await readdir(MIGRATIONS_DIR)).filter((name) => name.endsWith(".sql")).sort();
  for (const name of files.filter((file) => !applied.has(file))) {
    // Each file holds one statement. MySQL commits DDL immediately, so a file cannot be
    // rolled back; keeping them to one statement means a failure leaves nothing half-done.
    await pool.query(await readFile(path.join(MIGRATIONS_DIR, name), "utf8"));
    await pool.query("INSERT INTO schema_migrations (name) VALUES (?)", [name]);
    console.log(`applied ${name}`);
  }
  await pool.end();
}

migrate().catch((error) => {
  console.error(error);
  process.exit(1);
});
