import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const cacheDir = path.join(root, ".next");

try {
  fs.rmSync(cacheDir, { recursive: true, force: true });
  console.log("[eko] cleaned .next cache before starting dev server");
} catch {
  /* ignore */
}
