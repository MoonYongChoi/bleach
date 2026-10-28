import { readFileSync } from "node:fs";
import { Client } from "pg";
import { config } from "dotenv";

config({ path: ".env.local" });

const filePath = process.argv[2];
if (!filePath) {
  console.error("Usage: node scripts/run-sql.mjs <path-to-sql-file>");
  process.exit(1);
}

const sql = readFileSync(filePath, "utf8");

const client = new Client({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
});

try {
  await client.connect();
  await client.query(sql);
  console.log(`✔ Executed ${filePath} successfully.`);
} catch (err) {
  console.error("✘ Failed:", err.message);
  process.exit(1);
} finally {
  await client.end();
}
