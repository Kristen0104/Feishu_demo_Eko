import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { sanitizeMarkdownText } from "../../app/services/scripts/export_deck_to_pptx.mjs";

const execFileAsync = promisify(execFile);

test("sanitizeMarkdownText removes markdown markers before PPTX export", () => {
  assert.equal(
    sanitizeMarkdownText("**前端** [链接](https://example.com)"),
    "前端 链接",
  );
  assert.equal(sanitizeMarkdownText("- _风险_ 收敛"), "风险 收敛");
  assert.equal(sanitizeMarkdownText("1. __排期__ 对齐"), "排期 对齐");
  assert.equal(sanitizeMarkdownText("• 范围确认"), "范围确认");
  assert.equal(sanitizeMarkdownText("· 交付验收"), "交付验收");
  assert.equal(
    sanitizeMarkdownText({ title: "建模", body: "定义新布局 schema" }),
    "建模 | 定义新布局 schema",
  );
});

test("export_deck_to_pptx handles multiple layout payloads", async () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "pptx-layouts-"));
  const payloadPath = path.join(tempDir, "deck.json");
  const outputPath = path.join(tempDir, "deck.pptx");
  const scriptPath = path.resolve(
    "app/services/scripts/export_deck_to_pptx.mjs",
  );

  fs.writeFileSync(
    payloadPath,
    JSON.stringify({
      title: "多布局导出",
      theme: "business",
      slides: [
        { layout: "cover", title: "封面", subtitle: "试验版", kicker: "内部" },
        {
          layout: "section_divider",
          title: "第二章",
          subtitle: "结构扩展",
          kicker: "Catalog",
        },
        {
          layout: "quote",
          title: "结论",
          quote: "让结构自己说话。",
          source: "设计评审",
        },
        {
          layout: "two_column",
          title: "双栏",
          left_title: "左",
          right_title: "右",
          left: ["输入", "编排"],
          right: ["输出", "导出"],
        },
        { layout: "timeline", title: "时间线", items: ["启动", "联调", "验收"] },
        {
          layout: "process",
          title: "流程",
          items: ["输入整理", "结构生成", "PPTX 导出"],
        },
        {
          layout: "comparison",
          title: "方案对比",
          left_title: "旧版",
          right_title: "新版",
          left: ["bullets 偏多"],
          right: ["结构更丰富"],
        },
        {
          layout: "metrics",
          title: "指标",
          metrics: [{ label: "通过率", value: "98%", note: "核心链路" }],
        },
        {
          layout: "matrix",
          title: "矩阵",
          quadrants: [
            { title: "高价值高紧急", body: "导出链路" },
            { title: "高价值低紧急", body: "模板沉淀" },
            { title: "低价值高紧急", body: "文本修订" },
            { title: "低价值低紧急", body: "额外装饰" },
          ],
        },
        {
          layout: "architecture",
          title: "架构",
          blocks: [
            { title: "输入", body: "飞书 / 文本" },
            { title: "服务", body: "schema + HTML" },
            { title: "导出", body: "pptxgenjs" },
          ],
        },
        {
          layout: "summary",
          title: "总结",
          body: ["完成结构化输出"],
          actions: ["补齐校验"],
        },
      ],
    }),
    "utf8",
  );

  const { stdout } = await execFileAsync("node", [scriptPath, payloadPath, outputPath], {
    cwd: path.resolve("."),
  });
  const result = JSON.parse(stdout);

  assert.equal(result.path, outputPath);
  assert.equal(fs.existsSync(outputPath), true);
  assert.ok(fs.statSync(outputPath).size > 0);
});

test("export_deck_to_pptx normalizes timeline objects and strips duplicate bullets", async () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "pptx-sanitize-"));
  const payloadPath = path.join(tempDir, "deck.json");
  const outputPath = path.join(tempDir, "deck.pptx");
  const scriptPath = path.resolve(
    "app/services/scripts/export_deck_to_pptx.mjs",
  );

  fs.writeFileSync(
    payloadPath,
    JSON.stringify({
      title: "清洗测试",
      theme: "tech",
      slides: [
        {
          layout: "timeline",
          title: "里程碑",
          items: [
            {
              date: "2024 Q1",
              title: "启动项目",
              description: "完成范围定义",
            },
            "· 2024 Q2 完成联调",
          ],
        },
        {
          layout: "two_column",
          title: "风险拆解",
          left_title: "输入",
          right_title: "输出",
          left: ["• 风险识别", "- 范围确认"],
          right: ["1. 联调排期", "· 交付验收"],
        },
      ],
    }),
    "utf8",
  );

  await execFileAsync("node", [scriptPath, payloadPath, outputPath], {
    cwd: path.resolve("."),
  });

  const { stdout: timelineXml } = await execFileAsync("unzip", [
    "-p",
    outputPath,
    "ppt/slides/slide1.xml",
  ]);
  const { stdout: twoColumnXml } = await execFileAsync("unzip", [
    "-p",
    outputPath,
    "ppt/slides/slide2.xml",
  ]);

  assert.match(timelineXml, /2024 Q1 \| 启动项目 \| 完成范围定义/);
  assert.doesNotMatch(timelineXml, /\{'date':/);
  assert.match(timelineXml, /2024 Q2 完成联调/);
  assert.doesNotMatch(twoColumnXml, /• 风险识别/);
  assert.doesNotMatch(twoColumnXml, /- 范围确认/);
  assert.doesNotMatch(twoColumnXml, /1\. 联调排期/);
  assert.doesNotMatch(twoColumnXml, /· 交付验收/);
  assert.match(twoColumnXml, /风险识别/);
  assert.match(twoColumnXml, /范围确认/);
  assert.match(twoColumnXml, /联调排期/);
  assert.match(twoColumnXml, /交付验收/);
});

test("export_deck_to_pptx exports new structured layouts with editable text", async () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "pptx-new-layouts-"));
  const payloadPath = path.join(tempDir, "deck.json");
  const outputPath = path.join(tempDir, "deck.pptx");
  const scriptPath = path.resolve(
    "app/services/scripts/export_deck_to_pptx.mjs",
  );

  fs.writeFileSync(
    payloadPath,
    JSON.stringify({
      title: "新增布局导出",
      theme: "eco",
      slides: [
        {
          layout: "process",
          title: "流程页",
          items: [
            { title: "建模", body: "定义扩展 schema" },
            { title: "渲染", body: "生成 HTML 组件" },
            { title: "导出", body: "保持文本可编辑" },
          ],
        },
        {
          layout: "matrix",
          title: "矩阵页",
          quadrants: [
            { title: "高价值高紧急", body: "schema" },
            { title: "高价值低紧急", body: "视觉" },
            { title: "低价值高紧急", body: "文案" },
            { title: "低价值低紧急", body: "动画" },
          ],
        },
        {
          layout: "architecture",
          title: "架构页",
          blocks: [
            { title: "输入层", body: "聊天记录" },
            { title: "编排层", body: "PptService" },
            { title: "输出层", body: "HTML / PPTX" },
          ],
        },
      ],
    }),
    "utf8",
  );

  await execFileAsync("node", [scriptPath, payloadPath, outputPath], {
    cwd: path.resolve("."),
  });

  const { stdout: processXml } = await execFileAsync("unzip", [
    "-p",
    outputPath,
    "ppt/slides/slide1.xml",
  ]);
  const { stdout: matrixXml } = await execFileAsync("unzip", [
    "-p",
    outputPath,
    "ppt/slides/slide2.xml",
  ]);
  const { stdout: architectureXml } = await execFileAsync("unzip", [
    "-p",
    outputPath,
    "ppt/slides/slide3.xml",
  ]);

  assert.match(processXml, /建模/);
  assert.match(processXml, /定义扩展 schema/);
  assert.doesNotMatch(processXml, /\{'title':/);
  assert.match(matrixXml, /高价值高紧急/);
  assert.match(matrixXml, /schema/);
  assert.match(architectureXml, /输入层/);
  assert.match(architectureXml, /PptService/);
});

test("export_deck_to_pptx supports all new theme palettes", async () => {
  const themeCases = [
    { theme: "business", background: "002F6C" },
    { theme: "academic", background: "F8F8F8" },
    { theme: "apple_black", background: "1C1C1C" },
    { theme: "apple_white", background: "FFFFFF" },
    { theme: "eco", background: "DAD7CD" },
  ];

  for (const themeCase of themeCases) {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), `pptx-${themeCase.theme}-`));
    const payloadPath = path.join(tempDir, "deck.json");
    const outputPath = path.join(tempDir, "deck.pptx");
    const scriptPath = path.resolve(
      "app/services/scripts/export_deck_to_pptx.mjs",
    );

    fs.writeFileSync(
      payloadPath,
      JSON.stringify({
        title: `主题 ${themeCase.theme}`,
        theme: themeCase.theme,
        slides: [
          { layout: "cover", title: "封面", subtitle: "palette check", kicker: "test" },
        ],
      }),
      "utf8",
    );

    await execFileAsync("node", [scriptPath, payloadPath, outputPath], {
      cwd: path.resolve("."),
    });

    const { stdout: slideXml } = await execFileAsync("unzip", [
      "-p",
      outputPath,
      "ppt/slides/slide1.xml",
    ]);

    assert.match(slideXml, new RegExp(themeCase.background, "i"));
  }
});

test("export_deck_to_pptx normalizes legacy theme aliases to new palettes", async () => {
  const legacyCases = [
    { theme: "tech", background: "1C1C1C" },
    { theme: "jewel", background: "1C1C1C" },
    { theme: "apple", background: "FFFFFF" },
    { theme: "minimal", background: "FFFFFF" },
    { theme: "mint", background: "DAD7CD" },
    { theme: "sky", background: "F8F8F8" },
    { theme: "orange", background: "002F6C" },
  ];

  for (const themeCase of legacyCases) {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), `pptx-${themeCase.theme}-`));
    const payloadPath = path.join(tempDir, "deck.json");
    const outputPath = path.join(tempDir, "deck.pptx");
    const scriptPath = path.resolve(
      "app/services/scripts/export_deck_to_pptx.mjs",
    );

    fs.writeFileSync(
      payloadPath,
      JSON.stringify({
        title: `主题 ${themeCase.theme}`,
        theme: themeCase.theme,
        slides: [
          { layout: "cover", title: "封面", subtitle: "legacy alias", kicker: "test" },
        ],
      }),
      "utf8",
    );

    await execFileAsync("node", [scriptPath, payloadPath, outputPath], {
      cwd: path.resolve("."),
    });

    const { stdout: slideXml } = await execFileAsync("unzip", [
      "-p",
      outputPath,
      "ppt/slides/slide1.xml",
    ]);

    assert.match(slideXml, new RegExp(themeCase.background, "i"));
  }
});

test("export_deck_to_pptx uses a visible border palette for apple_white", async () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "pptx-apple-border-"));
  const payloadPath = path.join(tempDir, "deck.json");
  const outputPath = path.join(tempDir, "deck.pptx");
  const scriptPath = path.resolve(
    "app/services/scripts/export_deck_to_pptx.mjs",
  );

  fs.writeFileSync(
    payloadPath,
    JSON.stringify({
      title: "苹果白主题线条测试",
      theme: "apple_white",
      slides: [
        {
          layout: "timeline",
          title: "时间线",
          items: ["启动", "联调", "验收"],
        },
      ],
    }),
    "utf8",
  );

  await execFileAsync("node", [scriptPath, payloadPath, outputPath], {
    cwd: path.resolve("."),
  });

  const { stdout: slideXml } = await execFileAsync("unzip", [
    "-p",
    outputPath,
    "ppt/slides/slide1.xml",
  ]);

  assert.match(slideXml, /D9E2F0/i);
  assert.match(slideXml, /4A90E2/i);
});
