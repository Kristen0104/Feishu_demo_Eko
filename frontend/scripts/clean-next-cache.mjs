import { rmSync } from "node:fs";
import { resolve } from "node:path";

const nextDir = resolve(process.cwd(), ".next");

try {
  rmSync(nextDir, { force: true, recursive: true });
  console.log("[eko] cleaned .next cache before starting dev server");
} catch (error) {
  console.warn("[eko] failed to clean .next cache, continuing anyway");
  console.warn(error instanceof Error ? error.message : error);
}
