/**
 * Remove near-white squircle plate from Eko app icon PNGs (transparent trim),
 * then center on a square canvas for favicon / UI.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

function isWhitePlate(r, g, b) {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  if (max < 232) return false;
  if (max - min > 38) return false;
  return true;
}

async function ribbonFromSquirclePng(inputPath) {
  const input = sharp(inputPath).ensureAlpha();
  const { data, info } = await input.raw().toBuffer({ resolveWithObject: true });
  const { width, height, channels } = info;
  if (channels !== 4) throw new Error("Expected RGBA");

  const out = Buffer.from(data);
  for (let i = 0; i < out.length; i += 4) {
    const r = out[i];
    const g = out[i + 1];
    const b = out[i + 2];
    if (isWhitePlate(r, g, b)) {
      out[i + 3] = 0;
    }
  }

  return sharp(out, { raw: { width, height, channels: 4 } }).png().trim().toBuffer();
}

async function toSquarePng(buf, size) {
  const meta = await sharp(buf).metadata();
  const w = meta.width ?? size;
  const h = meta.height ?? size;
  const left = Math.max(0, Math.floor((size - w) / 2));
  const top = Math.max(0, Math.floor((size - h) / 2));
  return sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    },
  })
    .composite([{ input: buf, left, top }])
    .png()
    .toBuffer();
}

/** Scale trimmed ribbon so it fills ~88% of the square canvas (less empty margin). */
async function scaleToFillCanvas(buf, size, fillRatio = 0.88) {
  const meta = await sharp(buf).metadata();
  const w = meta.width ?? 1;
  const h = meta.height ?? 1;
  const target = size * fillRatio;
  const scale = Math.min(target / w, target / h);
  const nw = Math.max(1, Math.round(w * scale));
  const nh = Math.max(1, Math.round(h * scale));
  const resized = await sharp(buf).resize(nw, nh).png().toBuffer();
  return toSquarePng(resized, size);
}

async function main() {
  const squircle = path.join(root, "public", "eko-app-icon-squircle-source-1024.png");
  const fallback = path.join(root, "public", "eko-app-icon-squircle-source.png");
  const input = fs.existsSync(squircle) ? squircle : fallback;
  if (!fs.existsSync(input)) {
    console.error("Missing squircle source:", squircle, "or", fallback);
    process.exit(1);
  }

  const trimmed = await ribbonFromSquirclePng(input);
  const pub = path.join(root, "public");
  const appDir = path.join(root, "src", "app");
  const iconsDir = path.join(pub, "icons");

  fs.mkdirSync(iconsDir, { recursive: true });

  const master1024 = await scaleToFillCanvas(trimmed, 1024, 0.9);
  await sharp(master1024).png().toFile(path.join(pub, "eko-app-icon.png"));

  await sharp(master1024).resize(512, 512).png().toFile(path.join(iconsDir, "icon-512.png"));
  await sharp(master1024).resize(192, 192).png().toFile(path.join(iconsDir, "icon-192.png"));
  await fs.promises.copyFile(path.join(pub, "eko-app-icon.png"), path.join(appDir, "icon.png"));
  await sharp(master1024).resize(256, 256).png().toFile(path.join(appDir, "apple-icon.png"));

  const meta = await sharp(master1024).metadata();
  console.log("eko-app-icon.png", meta.width, meta.height, "ribbon-only, square");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
