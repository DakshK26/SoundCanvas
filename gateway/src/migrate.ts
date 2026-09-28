// tiny migration runner (didn't want a whole ORM for one table).
// runs any migrations/*.sql not in schema_migrations yet, in filename order.
// deploy.yml runs this as a one-off ECS task before rolling out the new code
import { readdir, readFile } from "fs/promises";
import path from "path";
import { RowDataPacket } from "mysql2/promise";
import { pool } from "./db";
import { log } from "./log";

const MIGRATIONS_DIR = path.join(__dirname, "..", "migrations");

async function migrate(): Promise<void> {
  await pool.query(`CREATE TABLE IF NOT EXISTS schema_migrations (
    name VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)`);
  const [rows] = await pool.query<RowDataPacket[]>("SELECT name FROM schema_migrations");
  const applied = new Set(rows.map((row) => row.name as string));

  const files = (await readdir(MIGRATIONS_DIR)).filter((name) => name.endsWith(".sql")).sort();
  for (const name of files.filter((file) => !applied.has(file))) {
    // one statement per file! mysql auto-commits DDL so there's no rolling back a file
    // halfway. one statement = it either happened or it didn't
    await pool.query(await readFile(path.join(MIGRATIONS_DIR, name), "utf8"));
    await pool.query("INSERT INTO schema_migrations (name) VALUES (?)", [name]);
    log.info("applied migration", { name });
  }
  await pool.end();
}

migrate().catch((error) => {
  log.error("migration failed", { error: (error as Error).message });
  process.exit(1);
});
