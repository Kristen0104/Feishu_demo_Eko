import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const PptxGenJS = require("pptxgenjs");

function readArg(flag) {
  const idx = process.argv.indexOf(flag);
  if (idx === -1 || idx + 1 >= process.argv.length) {
    throw new Error(`Missing required argument: ${flag}`);
  }
  return process.argv[idx + 1];
}

const htmlPath = readArg("--html");
const outputDir = readArg("--output-dir");
const pptxPath = readArg("--pptx");
const deckTitle = readArg("--title");
const width = Number.parseInt(readArg("--width"), 10);
const height = Number.parseInt(readArg("--height"), 10);
const deviceScaleFactor = Number.parseFloat(readArg("--device-scale-factor"));

await fs.mkdir(outputDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width, height },
  deviceScaleFactor,
});

try {
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
  await page.waitForTimeout(1500);
  await page.addStyleTag({
    content: `
      #nav, #hint { display: none !important; }
      [data-anim] { opacity: 1 !important; transform: none !important; }
    `,
  });

  const slideCount = await page.locator(".slide").count();
  const slideImagePaths = [];

  for (let index = 0; index < slideCount; index += 1) {
    await page.evaluate((n) => {
      if (typeof window.go === "function") {
        window.go(n);
      }
    }, index);
    await page.waitForTimeout(900);
    const imagePath = path.join(outputDir, `slide-${String(index + 1).padStart(2, "0")}.png`);
    await page.screenshot({ path: imagePath });
    slideImagePaths.push(imagePath);
  }

  const pptx = new PptxGenJS();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = "Eko";
  pptx.company = "Eko";
  pptx.subject = deckTitle;
  pptx.title = deckTitle;

  for (const imagePath of slideImagePaths) {
    const slide = pptx.addSlide();
    slide.addImage({
      path: imagePath,
      x: 0,
      y: 0,
      w: 13.333,
      h: 7.5,
    });
  }

  await pptx.writeFile({ fileName: pptxPath });
  process.stdout.write(
    JSON.stringify({
      pptxPath,
      slideImagePaths,
      slideCount,
    }),
  );
} finally {
  await page.close();
  await browser.close();
}
