import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const MARKDOWN_LINK_RE = /\[([^\]]+)\]\(([^)]+)\)/g;
const MARKDOWN_STRONG_RE = /(\*\*|__)(.+?)\1/g;
const MARKDOWN_EMPHASIS_RE =
  /(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)|(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)/g;
const LEADING_LIST_MARKER_RE = /^\s*(?:(?:[-+*•·])|(?:\d+[.)])|(?:[A-Za-z][.)]))\s+/;
const INLINE_CODE_RE = /`([^`]+)`/g;

function formatTimelineItem(value) {
  if (value == null) {
    return "";
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    return sanitizeMarkdownText(value);
  }

  const preferredKeys = ["date", "title", "subtitle", "body", "description", "source", "note"];
  const preferred = preferredKeys
    .map((key) => sanitizeMarkdownText(value[key]))
    .filter(Boolean);
  if (preferred.length) {
    return preferred.join(" | ");
  }

  return Object.values(value)
    .map((item) => sanitizeMarkdownText(item))
    .filter(Boolean)
    .join(" | ");
}

function normalizeComponentItems(items, fallbackTitle = "模块") {
  return (items || [])
    .filter(Boolean)
    .map((item) => {
      if (typeof item === "object" && !Array.isArray(item)) {
        const title =
          sanitizeMarkdownText(item.title) ||
          sanitizeMarkdownText(item.label) ||
          fallbackTitle;
        const body =
          sanitizeMarkdownText(item.body) ||
          sanitizeMarkdownText(item.description) ||
          sanitizeMarkdownText(item.subtitle) ||
          "";
        const source = sanitizeMarkdownText(item.source) || "";
        return { title, body, source };
      }
      return { title: sanitizeMarkdownText(item) || fallbackTitle, body: "", source: "" };
    })
    .filter((item) => item.title || item.body);
}

export function sanitizeMarkdownText(value) {
  if (value == null) {
    return "";
  }

  if (typeof value === "object" && !Array.isArray(value)) {
    return formatTimelineItem(value);
  }

  let cleaned = String(value).trim();
  if (!cleaned) {
    return "";
  }

  let previous = null;
  while (cleaned !== previous) {
    previous = cleaned;
    cleaned = cleaned.replace(MARKDOWN_LINK_RE, "$1");
    cleaned = cleaned.replace(MARKDOWN_STRONG_RE, "$2");
    cleaned = cleaned.replace(
      MARKDOWN_EMPHASIS_RE,
      (_, starValue, underscoreValue) => starValue || underscoreValue || "",
    );
    cleaned = cleaned.replace(INLINE_CODE_RE, "$1");
  }

  return cleaned.replace(LEADING_LIST_MARKER_RE, "").replace(/\s+/g, " ").trim();
}

function sanitizeDeckForExport(deck) {
  return {
    ...deck,
    title: sanitizeMarkdownText(deck.title) || "Deck",
    author: sanitizeMarkdownText(deck.author) || deck.author,
    slides: (deck.slides || []).map((slide) => ({
      ...slide,
      layout: sanitizeLayout(slide.layout),
      title: sanitizeMarkdownText(slide.title) || "Slide",
      body: (slide.body || [])
        .map((item) => sanitizeMarkdownText(item))
        .filter((item) => item),
      subtitle: sanitizeMarkdownText(slide.subtitle) || slide.subtitle,
      kicker: sanitizeMarkdownText(slide.kicker) || slide.kicker,
      quote: sanitizeMarkdownText(slide.quote) || slide.quote,
      source: sanitizeMarkdownText(slide.source) || slide.source,
      left_title: sanitizeMarkdownText(slide.left_title) || slide.left_title,
      right_title: sanitizeMarkdownText(slide.right_title) || slide.right_title,
      left: (slide.left || [])
        .map((item) => sanitizeMarkdownText(item))
        .filter((item) => item),
      right: (slide.right || [])
        .map((item) => sanitizeMarkdownText(item))
        .filter((item) => item),
      items: (slide.items || [])
        .map((item) => sanitizeMarkdownText(item))
        .filter((item) => item),
      quadrants: normalizeComponentItems(slide.quadrants, "象限"),
      blocks: normalizeComponentItems(slide.blocks || slide.items, "模块"),
      metrics: (slide.metrics || [])
        .filter((metric) => metric && typeof metric === "object")
        .map((metric) => ({
          label: sanitizeMarkdownText(metric.label) || "指标",
          value: sanitizeMarkdownText(metric.value) || "-",
          note: sanitizeMarkdownText(metric.note) || null,
        })),
      actions: (slide.actions || [])
        .map((item) => sanitizeMarkdownText(item))
        .filter((item) => item),
      notes: sanitizeMarkdownText(slide.notes) || slide.notes,
    })),
  };
}

function normalizeThemeId(value) {
  const normalized = String(value || "").trim().toLowerCase();
  const themeMap = {
    business: "business",
    business风: "business",
    商务: "business",
    商务风: "business",
    商业: "business",
    orange: "business",
    活泼: "business",
    活泼橙: "business",
    academic: "academic",
    学术: "academic",
    学术风: "academic",
    sky: "academic",
    天空: "academic",
    天空蓝: "academic",
    apple_black: "apple_black",
    苹果黑风: "apple_black",
    tech: "apple_black",
    jewel: "apple_black",
    宝石: "apple_black",
    宝石蓝: "apple_black",
    科技: "apple_black",
    科技风: "apple_black",
    apple_white: "apple_white",
    apple: "apple_white",
    苹果白风: "apple_white",
    minimal: "apple_white",
    simple: "apple_white",
    简约: "apple_white",
    简约风: "apple_white",
    eco: "eco",
    绿色环保风: "eco",
    mint: "eco",
    薄荷: "eco",
    薄荷绿: "eco",
  };
  return themeMap[normalized] || "apple_white";
}

function sanitizeLayout(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return [
    "cover",
    "bullets",
    "two_column",
    "timeline",
    "metrics",
    "summary",
    "section_divider",
    "quote",
    "comparison",
    "process",
    "matrix",
    "architecture",
  ].includes(normalized)
    ? normalized
    : "bullets";
}

function addHeader(slide, deck, palette, slideData) {
  slide.addText(deck.title || "Deck", {
    x: 0.4,
    y: 0.28,
    w: 8.8,
    h: 0.4,
    fontSize: 22,
    bold: true,
    color: palette.title,
  });
  slide.addText(`v${slideData.version || 1}`, {
    x: 11.1,
    y: 0.34,
    w: 1.0,
    h: 0.3,
    align: "right",
    fontSize: 10,
    color: palette.title,
  });
}

function addNotes(slide, palette, notes) {
  if (!notes) {
    return;
  }
  slide.addText(notes, {
    x: 0.7,
    y: 6.65,
    w: 11.0,
    h: 0.35,
    fontSize: 11,
    color: palette.muted,
    transparency: 20,
    italic: true,
  });
}

function asBullets(items, fallback = "待补充内容") {
  const normalized = (items || []).filter(Boolean).map((item) => ({
    text: sanitizeMarkdownText(item),
    options: { bullet: { indent: 14 } },
  }));
  return normalized.length ? normalized : [{ text: fallback }];
}

function addCoverSlide(slide, deck, palette, slideData) {
  slide.addText(slideData.kicker || deck.title || "Deck", {
    x: 1.2,
    y: 1.2,
    w: 10.0,
    h: 0.4,
    align: "center",
    fontSize: 16,
    bold: true,
    color: palette.title,
  });
  slide.addText(slideData.title || "Slide", {
    x: 1.0,
    y: 2.1,
    w: 10.4,
    h: 1.0,
    align: "center",
    fontSize: 28,
    bold: true,
    color: palette.title,
  });
  if (slideData.subtitle) {
    slide.addText(slideData.subtitle, {
      x: 1.3,
      y: 3.3,
      w: 9.8,
      h: 0.6,
      align: "center",
      fontSize: 17,
      color: palette.body,
      transparency: 18,
    });
  }
}

function addBulletsSlide(slide, palette, slideData) {
  slide.addText(slideData.title || "Slide", {
    x: 0.6,
    y: 1.1,
    w: 11.2,
    h: 0.7,
    fontSize: 22,
    bold: true,
    color: palette.title,
  });
  slide.addText(asBullets(slideData.body), {
    x: 0.9,
    y: 2.0,
    w: 11.0,
    h: 4.2,
    fontSize: 18,
    color: palette.body,
    breakLine: true,
    margin: 0.1,
  });
}

function addSectionDividerSlide(slide, palette, slideData) {
  slide.addShape("rect", {
    x: 0.75,
    y: 1.2,
    w: 10.8,
    h: 4.9,
    line: { color: palette.line, width: 1 },
    fill: { color: palette.card, transparency: 6 },
  });
  slide.addShape("rect", {
    x: 0.75,
    y: 1.2,
    w: 0.18,
    h: 4.9,
    line: { color: palette.component, width: 0 },
    fill: { color: palette.component },
  });
  if (slideData.kicker) {
    slide.addText(slideData.kicker, {
      x: 1.15,
      y: 1.7,
      w: 2.5,
      h: 0.3,
      fontSize: 14,
      bold: true,
      color: palette.component,
    });
  }
  slide.addText(slideData.title || "Section", {
    x: 1.15,
    y: 2.35,
    w: 8.8,
    h: 0.9,
    fontSize: 30,
    bold: true,
    color: palette.title,
  });
  if (slideData.subtitle) {
    slide.addText(slideData.subtitle, {
      x: 1.15,
      y: 3.45,
      w: 8.2,
      h: 0.7,
      fontSize: 18,
      color: palette.body,
      transparency: 10,
    });
  }
}

function addQuoteSlide(slide, palette, slideData) {
  slide.addShape("rect", {
    x: 0.8,
    y: 1.45,
    w: 10.7,
    h: 4.5,
    line: { color: palette.line, width: 1 },
    fill: { color: palette.card, transparency: 4 },
  });
  slide.addText("“", {
    x: 1.1,
    y: 1.7,
    w: 0.7,
    h: 0.8,
    fontSize: 42,
    bold: true,
    color: palette.component,
  });
  slide.addText(slideData.title || "结论", {
    x: 2.0,
    y: 1.75,
    w: 8.8,
    h: 0.45,
    fontSize: 18,
    bold: true,
    color: palette.title,
  });
  slide.addText(slideData.quote || "待补充结论", {
    x: 2.0,
    y: 2.35,
    w: 8.7,
    h: 1.9,
    fontSize: 24,
    bold: true,
    color: palette.title,
    breakLine: true,
    margin: 0.02,
  });
  if (slideData.source) {
    slide.addText(slideData.source, {
      x: 2.0,
      y: 4.65,
      w: 4.0,
      h: 0.3,
      fontSize: 13,
      color: palette.muted,
      italic: true,
    });
  }
}

function addTwoColumnSlide(slide, palette, slideData) {
  slide.addText(slideData.title || "Slide", {
    x: 0.6,
    y: 1.0,
    w: 11.2,
    h: 0.6,
    fontSize: 22,
    bold: true,
    color: palette.muted,
  });
  slide.addShape("rect", {
    x: 0.7,
    y: 1.9,
    w: 5.2,
    h: 3.9,
    line: { color: palette.line },
    fill: { color: palette.card },
  });
  slide.addShape("rect", {
    x: 6.1,
    y: 1.9,
    w: 5.2,
    h: 3.9,
    line: { color: palette.line },
    fill: { color: palette.card },
  });
  slide.addText(slideData.left_title || "左侧", {
    x: 1.0,
    y: 2.1,
    w: 4.4,
    h: 0.4,
    fontSize: 16,
    bold: true,
    color: palette.title,
  });
  slide.addText(slideData.right_title || "右侧", {
    x: 6.4,
    y: 2.1,
    w: 4.4,
    h: 0.4,
    fontSize: 16,
    bold: true,
    color: palette.title,
  });
  slide.addText(asBullets(slideData.left), {
    x: 1.0,
    y: 2.6,
    w: 4.4,
    h: 2.8,
    fontSize: 16,
    color: palette.title,
    breakLine: true,
    margin: 0.08,
  });
  slide.addText(asBullets(slideData.right), {
    x: 6.4,
    y: 2.6,
    w: 4.4,
    h: 2.8,
    fontSize: 16,
    color: palette.body,
    breakLine: true,
    margin: 0.08,
  });
}

function addTimelineSlide(slide, palette, slideData) {
  slide.addText(slideData.title || "Slide", {
    x: 0.6,
    y: 1.0,
    w: 11.2,
    h: 0.6,
    fontSize: 22,
    bold: true,
    color: palette.title,
  });
  const items = (slideData.items && slideData.items.length ? slideData.items : ["待补充时间节点"]).slice(0, 5);
  slide.addShape("line", {
    x: 1.0,
    y: 3.2,
    w: 9.8,
    h: 0,
    line: { color: palette.line, width: 2 },
  });
  items.forEach((item, index) => {
    const step = items.length === 1 ? 0 : 9.0 / (items.length - 1);
    const x = 1.0 + step * index;
    slide.addShape("ellipse", {
      x,
      y: 3.02,
      w: 0.22,
      h: 0.22,
      fill: { color: palette.component },
      line: { color: palette.line },
    });
    slide.addText(item, {
      x: Math.max(0.6, x - 0.5),
      y: 3.45,
      w: 1.5,
      h: 1.1,
      align: "center",
      fontSize: 14,
      color: palette.body,
    });
  });
}

function addProcessSlide(slide, palette, slideData) {
  slide.addText(slideData.title || "Slide", {
    x: 0.6,
    y: 1.0,
    w: 11.2,
    h: 0.6,
    fontSize: 22,
    bold: true,
    color: palette.title,
  });
  const items = (slideData.items && slideData.items.length ? slideData.items : ["待补充流程"]).slice(0, 4);
  items.forEach((item, index) => {
    const x = 0.8 + index * 2.82;
    slide.addShape("rect", {
      x,
      y: 2.15,
      w: 2.4,
      h: 2.2,
      line: { color: palette.line, width: 1 },
      fill: { color: palette.card, transparency: 4 },
    });
    slide.addShape("ellipse", {
      x: x + 0.16,
      y: 2.28,
      w: 0.32,
      h: 0.32,
      line: { color: palette.component, width: 1 },
      fill: { color: palette.component },
    });
    slide.addText(String(index + 1), {
      x: x + 0.22,
      y: 2.33,
      w: 0.18,
      h: 0.14,
      fontSize: 10,
      bold: true,
      color: palette.secondary,
      align: "center",
    });
    slide.addText(item, {
      x: x + 0.22,
      y: 2.82,
      w: 1.95,
      h: 1.1,
      fontSize: 15,
      color: palette.body,
      breakLine: true,
      margin: 0.02,
    });
    if (index < items.length - 1) {
      slide.addShape("line", {
        x: x + 2.4,
        y: 3.22,
        w: 0.42,
        h: 0,
        line: { color: palette.line, width: 1.5 },
      });
    }
  });
}

function addMetricsSlide(slide, palette, slideData) {
  slide.addText(slideData.title || "Slide", {
    x: 0.6,
    y: 1.0,
    w: 11.2,
    h: 0.6,
    fontSize: 22,
    bold: true,
    color: palette.title,
  });
  const metrics = (slideData.metrics && slideData.metrics.length
    ? slideData.metrics
    : [{ label: "关键指标", value: "待补充", note: null }]).slice(0, 4);
  metrics.forEach((metric, index) => {
    const col = index % 2;
    const row = Math.floor(index / 2);
    const x = 0.9 + col * 5.45;
    const y = 1.9 + row * 2.1;
    slide.addShape("rect", {
      x,
      y,
      w: 4.8,
      h: 1.7,
      line: { color: palette.line },
      fill: { color: palette.card },
    });
    slide.addText(metric.label, {
      x: x + 0.25,
      y: y + 0.18,
      w: 4.0,
      h: 0.3,
      fontSize: 15,
      bold: true,
      color: palette.title,
    });
    slide.addText(metric.value, {
      x: x + 0.25,
      y: y + 0.56,
      w: 4.0,
      h: 0.45,
      fontSize: 24,
      bold: true,
      color: palette.component,
    });
    if (metric.note) {
      slide.addText(metric.note, {
        x: x + 0.25,
        y: y + 1.08,
        w: 4.1,
        h: 0.25,
        fontSize: 11,
        color: palette.body,
        transparency: 24,
      });
    }
  });
}

function addSummarySlide(slide, palette, slideData) {
  slide.addText(slideData.title || "Slide", {
    x: 0.6,
    y: 1.0,
    w: 11.2,
    h: 0.6,
    fontSize: 22,
    bold: true,
    color: palette.title,
  });
  slide.addShape("rect", {
    x: 0.8,
    y: 1.9,
    w: 6.2,
    h: 3.8,
    line: { color: palette.line },
    fill: { color: palette.card },
  });
  slide.addShape("rect", {
    x: 7.3,
    y: 1.9,
    w: 4.0,
    h: 3.8,
    line: { color: palette.line },
    fill: { color: palette.card },
  });
  slide.addText("总结", {
    x: 1.05,
    y: 2.1,
    w: 1.2,
    h: 0.3,
    fontSize: 16,
    bold: true,
    color: palette.title,
  });
  slide.addText("行动项", {
    x: 7.55,
    y: 2.1,
    w: 1.4,
    h: 0.3,
    fontSize: 16,
    bold: true,
    color: palette.title,
  });
  slide.addText(asBullets(slideData.body, "待补充总结"), {
    x: 1.05,
    y: 2.55,
    w: 5.5,
    h: 2.7,
    fontSize: 16,
    color: palette.body,
    breakLine: true,
    margin: 0.08,
  });
  slide.addText(asBullets(slideData.actions, "待补充行动项"), {
    x: 7.55,
    y: 2.55,
    w: 3.1,
    h: 2.7,
    fontSize: 15,
    color: palette.body,
    breakLine: true,
    margin: 0.08,
  });
}

function addComparisonSlide(slide, palette, slideData) {
  slide.addText(slideData.title || "Slide", {
    x: 0.6,
    y: 1.0,
    w: 11.2,
    h: 0.6,
    fontSize: 22,
    bold: true,
    color: palette.title,
  });
  [
    { x: 0.8, title: slideData.left_title || "方案 A", items: slideData.left || ["待补充"] },
    { x: 6.2, title: slideData.right_title || "方案 B", items: slideData.right || ["待补充"] },
  ].forEach((column) => {
    slide.addShape("rect", {
      x: column.x,
      y: 1.95,
      w: 4.9,
      h: 3.9,
      line: { color: palette.line, width: 1 },
      fill: { color: palette.card },
    });
    slide.addShape("rect", {
      x: column.x,
      y: 1.95,
      w: 4.9,
      h: 0.14,
      line: { color: palette.component, width: 0 },
      fill: { color: palette.component },
    });
    slide.addText(column.title, {
      x: column.x + 0.24,
      y: 2.2,
      w: 4.0,
      h: 0.3,
      fontSize: 16,
      bold: true,
      color: palette.title,
    });
    slide.addText(asBullets(column.items), {
      x: column.x + 0.24,
      y: 2.7,
      w: 4.15,
      h: 2.65,
      fontSize: 15,
      color: palette.body,
      breakLine: true,
      margin: 0.06,
    });
  });
}

function addMatrixSlide(slide, palette, slideData) {
  slide.addText(slideData.title || "Slide", {
    x: 0.6,
    y: 1.0,
    w: 11.2,
    h: 0.6,
    fontSize: 22,
    bold: true,
    color: palette.title,
  });
  const quadrants = (slideData.quadrants && slideData.quadrants.length
    ? slideData.quadrants
    : normalizeComponentItems([
        { title: "高价值高紧急", body: "待补充" },
        { title: "高价值低紧急", body: "待补充" },
        { title: "低价值高紧急", body: "待补充" },
        { title: "低价值低紧急", body: "待补充" },
      ])).slice(0, 4);
  quadrants.forEach((item, index) => {
    const col = index % 2;
    const row = Math.floor(index / 2);
    const x = 0.9 + col * 5.35;
    const y = 1.9 + row * 2.0;
    slide.addShape("rect", {
      x,
      y,
      w: 4.75,
      h: 1.6,
      line: { color: palette.line, width: 1 },
      fill: { color: palette.card, transparency: 2 },
    });
    slide.addText(item.title, {
      x: x + 0.2,
      y: y + 0.18,
      w: 4.1,
      h: 0.3,
      fontSize: 15,
      bold: true,
      color: palette.title,
    });
    slide.addText(item.body || "", {
      x: x + 0.2,
      y: y + 0.62,
      w: 4.1,
      h: 0.58,
      fontSize: 13,
      color: palette.body,
      breakLine: true,
      margin: 0.02,
    });
  });
}

function addArchitectureSlide(slide, palette, slideData) {
  slide.addText(slideData.title || "Slide", {
    x: 0.6,
    y: 1.0,
    w: 11.2,
    h: 0.6,
    fontSize: 22,
    bold: true,
    color: palette.title,
  });
  const blocks = (slideData.blocks && slideData.blocks.length
    ? slideData.blocks
    : normalizeComponentItems(slideData.items || [{ title: "模块", body: "待补充" }], "模块")).slice(0, 4);
  blocks.forEach((item, index) => {
    const x = 0.85 + index * 2.7;
    slide.addShape("rect", {
      x,
      y: 2.35,
      w: 2.25,
      h: 2.05,
      line: { color: palette.line, width: 1 },
      fill: { color: palette.card, transparency: 2 },
    });
    slide.addText(item.title, {
      x: x + 0.18,
      y: 2.63,
      w: 1.85,
      h: 0.36,
      fontSize: 15,
      bold: true,
      color: palette.title,
      align: "center",
    });
    slide.addText(item.body || "", {
      x: x + 0.18,
      y: 3.13,
      w: 1.85,
      h: 0.72,
      fontSize: 12,
      color: palette.body,
      breakLine: true,
      margin: 0.03,
      align: "center",
      valign: "mid",
    });
    if (index < blocks.length - 1) {
      slide.addShape("line", {
        x: x + 2.25,
        y: 3.38,
        w: 0.45,
        h: 0,
        line: { color: palette.line, width: 1.5 },
      });
    }
  });
}

async function main() {
  const [, , payloadPath, pptxPath] = process.argv;

  if (!payloadPath || !pptxPath) {
    console.error("usage: export_deck_to_pptx.mjs <payload.json> <output.pptx> [htmlPath]");
    process.exit(1);
  }

  let pptxgen;
  try {
    ({ default: pptxgen } = await import("pptxgenjs"));
  } catch (error) {
    console.error(`pptxgenjs unavailable: ${error.message}`);
    process.exit(2);
  }

  const raw = fs.readFileSync(payloadPath, "utf8");
  const deck = sanitizeDeckForExport(JSON.parse(raw));
  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = deck.author || "Eko";
  pptx.subject = deck.title || "HTML PPT Export";
  pptx.title = deck.title || "Deck";
  pptx.company = "Eko";
  pptx.lang = "zh-CN";
  pptx.theme = {
    headFontFace: "Arial",
    bodyFontFace: "Arial",
    lang: "zh-CN",
  };

  const colorMap = {
    business: {
      bg: "002F6C",
      title: "FFFFFF",
      body: "F2F2F2",
      component: "4F81BD",
      secondary: "FFFFFF",
      line: "4F81BD",
      card: "4F81BD",
      muted: "D9E6F2",
    },
    academic: {
      bg: "F8F8F8",
      title: "1A2E42",
      body: "333333",
      component: "4A90E2",
      secondary: "FFFFFF",
      line: "D6E7F8",
      card: "FFFFFF",
      muted: "5B6B7A",
    },
    apple_black: {
      bg: "1C1C1C",
      title: "FFFFFF",
      body: "E5E5E5",
      component: "FFD700",
      secondary: "2A2A2A",
      line: "5A5A5A",
      card: "2A2A2A",
      muted: "A9A9A9",
    },
    apple_white: {
      bg: "FFFFFF",
      title: "000000",
      body: "222222",
      component: "4A90E2",
      secondary: "F0F4FA",
      line: "D9E2F0",
      card: "FFFFFF",
      muted: "5A6470",
    },
    eco: {
      bg: "DAD7CD",
      title: "333333",
      body: "333333",
      component: "588157",
      secondary: "A3B18A",
      line: "3A5A40",
      card: "A3B18A",
      muted: "4C5F46",
    },
  };
  const palette = colorMap[normalizeThemeId(deck.theme)] || colorMap.apple_white;

  for (const slideData of deck.slides || []) {
    const slide = pptx.addSlide();
    slide.background = { color: palette.bg };
    addHeader(slide, deck, palette, slideData);
    switch (slideData.layout) {
      case "cover":
        addCoverSlide(slide, deck, palette, slideData);
        break;
      case "section_divider":
        addSectionDividerSlide(slide, palette, slideData);
        break;
      case "quote":
        addQuoteSlide(slide, palette, slideData);
        break;
      case "two_column":
        addTwoColumnSlide(slide, palette, slideData);
        break;
      case "comparison":
        addComparisonSlide(slide, palette, slideData);
        break;
      case "timeline":
        addTimelineSlide(slide, palette, slideData);
        break;
      case "process":
        addProcessSlide(slide, palette, slideData);
        break;
      case "metrics":
        addMetricsSlide(slide, palette, slideData);
        break;
      case "matrix":
        addMatrixSlide(slide, palette, slideData);
        break;
      case "architecture":
        addArchitectureSlide(slide, palette, slideData);
        break;
      case "summary":
        addSummarySlide(slide, palette, slideData);
        break;
      default:
        addBulletsSlide(slide, palette, slideData);
        break;
    }
    addNotes(slide, palette, slideData.notes);
  }

  fs.mkdirSync(path.dirname(pptxPath), { recursive: true });
  await pptx.writeFile({ fileName: pptxPath });
  process.stdout.write(JSON.stringify({ path: path.resolve(pptxPath), url: null }));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
