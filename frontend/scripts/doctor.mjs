import fs from "fs";
import path from "path";

const cwd = process.cwd();
const checks = [
  {
    name: "node_modules present",
    ok: () => fs.existsSync(path.join(cwd, "node_modules")),
    hint: "Run `npm ci` (recommended) or `npm install`.",
  },
  {
    name: "package-lock present",
    ok: () => fs.existsSync(path.join(cwd, "package-lock.json")),
    hint: "This repo expects npm lockfile. If missing, run `npm install` to generate.",
  },
  {
    name: "enhanced-resolve not broken",
    ok: () =>
      fs.existsSync(path.join(cwd, "node_modules/enhanced-resolve/lib/DescriptionFileUtils.js")) &&
      fs.existsSync(path.join(cwd, "node_modules/enhanced-resolve/lib/forEachBail.js")),
    hint:
      "Your install is incomplete/corrupted. Delete `node_modules` and run `npm ci`.",
  },
  {
    name: "@alloc/quick-lru not broken",
    ok: () =>
      fs.existsSync(path.join(cwd, "node_modules/@alloc/quick-lru/package.json")) &&
      fs.existsSync(path.join(cwd, "node_modules/@alloc/quick-lru/index.js")),
    hint:
      "Your install is incomplete/corrupted. Delete `node_modules/@alloc/quick-lru` then `npm ci`.",
  },
  {
    name: ".next not locked",
    ok: () => !fs.existsSync(path.join(cwd, ".next/lock")),
    hint: "Remove `.next/lock` (or delete `.next`) then restart `npm run dev`.",
  },
];

let failed = 0;
for (const c of checks) {
  const ok = Boolean(c.ok());
  if (!ok) failed += 1;
  process.stdout.write(`${ok ? "✅" : "❌"} ${c.name}\n`);
  if (!ok && c.hint) process.stdout.write(`   ↳ ${c.hint}\n`);
}

if (failed) {
  process.stdout.write(`\nDoctor: ${failed} check(s) failed.\n`);
  process.exit(1);
}

process.stdout.write("\nDoctor: OK.\n");

