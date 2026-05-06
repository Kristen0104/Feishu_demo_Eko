import type { Editor } from "@tldraw/editor";
import type { TLGeoShape, TLShapeId } from "@tldraw/tlschema";
import { createShapeId } from "@tldraw/tlschema";
import { renderRichTextFromHTML } from "tldraw";

function escapeHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export type StoryCardSpec = {
  title: string;
  subtitle?: string;
  accent: "violet" | "blue";
};

export type StoryStreamOptions = {
  /** 系统「减少动态效果」 */
  reducedMotion: boolean;
  /** 模拟每条 WebSocket 消息到达前的间隔（毫秒） */
  mockWsMessageGapMs: number;
  /** 单笔形状入场动画时长（animateShapes） */
  shapeRevealDurationMs: number;
};

const LAYOUT = {
  startX: 96,
  startY: 260,
  cardW: 300,
  cardH: 148,
  stepX: 360,
} as const;

function sleep(ms: number) {
  return new Promise<void>((r) => window.setTimeout(r, ms));
}

/** 移除上一轮 Agent 演示生成的形状，避免重复叠加 */
export function removeEkoAgentShapes(editor: Editor) {
  const shapes = editor.getCurrentPageShapes();
  const ids = shapes
    .filter((s) => {
      const m = s.meta as Record<string, unknown> | undefined;
      return Boolean(m?.ekoAgentStory || m?.ekoConnector || m?.ekoStream);
    })
    .map((s) => s.id);
  if (ids.length) editor.deleteShapes(ids);
}

type StoryStep =
  | { kind: "card"; card: StoryCardSpec; index: number }
  | { kind: "connector"; afterIndex: number };

function buildStorySteps(cards: StoryCardSpec[]): StoryStep[] {
  const steps: StoryStep[] = [];
  cards.forEach((card, i) => {
    steps.push({ kind: "card", card, index: i });
    if (i < cards.length - 1) steps.push({ kind: "connector", afterIndex: i });
  });
  return steps;
}

function createCardShape(editor: Editor, pageId: TLShapeId | string, card: StoryCardSpec, index: number): TLShapeId {
  const id = createShapeId();
  const html = card.subtitle
    ? `<p><strong>${escapeHtml(card.title)}</strong></p><p>${escapeHtml(card.subtitle)}</p>`
    : `<p><strong>${escapeHtml(card.title)}</strong></p>`;

  editor.createShapes<TLGeoShape>([
    {
      id,
      type: "geo",
      parentId: pageId as TLShapeId,
      x: LAYOUT.startX + index * LAYOUT.stepX,
      y: LAYOUT.startY,
      rotation: 0,
      opacity: 0,
      meta: { ekoAgentStory: true, ekoStream: true },
      props: {
        geo: "rectangle",
        w: LAYOUT.cardW,
        h: LAYOUT.cardH,
        growY: 0,
        scale: 0.05,
        color: card.accent === "violet" ? "light-violet" : "light-blue",
        fill: "semi",
        dash: "solid",
        size: "m",
        font: "sans",
        align: "middle",
        verticalAlign: "middle",
        richText: renderRichTextFromHTML(editor, html),
        labelColor: "black",
        url: "",
      },
    },
  ]);
  return id;
}

function createConnectorShape(editor: Editor, pageId: TLShapeId | string, afterIndex: number): TLShapeId {
  const id = createShapeId();
  const cx = LAYOUT.startX + afterIndex * LAYOUT.stepX + LAYOUT.cardW + 12;
  const cy = LAYOUT.startY + LAYOUT.cardH / 2 - 5;

  editor.createShapes<TLGeoShape>([
    {
      id,
      type: "geo",
      parentId: pageId as TLShapeId,
      x: cx,
      y: cy,
      rotation: 0,
      opacity: 0,
      meta: { ekoConnector: true, ekoStream: true },
      props: {
        geo: "rectangle",
        w: 40,
        h: 10,
        growY: 0,
        scale: 0.05,
        color: "grey",
        fill: "solid",
        dash: "dotted",
        size: "s",
        font: "sans",
        align: "middle",
        verticalAlign: "middle",
        richText: renderRichTextFromHTML(editor, "<p></p>"),
        labelColor: "grey",
        url: "",
      },
    },
  ]);
  return id;
}

/** 使用 editor.animateShapes 播放入场；无障碍下一帧拉满 */
function revealGeoShape(editor: Editor, id: TLShapeId, opts: Pick<StoryStreamOptions, "reducedMotion" | "shapeRevealDurationMs">) {
  if (opts.reducedMotion) {
    editor.updateShapes([{ id, type: "geo", opacity: 1, props: { scale: 1 } }]);
    return;
  }
  editor.animateShapes(
    [{ id, type: "geo", opacity: 1, props: { scale: 1 } }],
    {
      animation: {
        duration: opts.shapeRevealDurationMs,
        easing: (t) => 1 - (1 - t) ** 3,
      },
    },
  );
}

/**
 * 模拟远端 Agent 经 WebSocket 一笔一笔推送：每条「消息」间隔 mockWsMessageGapMs，
 * 再用 animateShapes Reveal。生产环境可将 sleep 替换为 await nextWsPayload()。
 */
export async function streamAgentStoryboard(editor: Editor, cards: StoryCardSpec[], rawOpts: Partial<StoryStreamOptions> = {}) {
  const opts: StoryStreamOptions = {
    reducedMotion: rawOpts.reducedMotion ?? false,
    mockWsMessageGapMs: rawOpts.reducedMotion ? 0 : (rawOpts.mockWsMessageGapMs ?? 380),
    shapeRevealDurationMs: rawOpts.reducedMotion ? 1 : (rawOpts.shapeRevealDurationMs ?? 520),
  };

  removeEkoAgentShapes(editor);

  const pageId = editor.getCurrentPageId();
  const steps = buildStorySteps(cards);
  if (steps.length === 0) return [];

  const createdIds: TLShapeId[] = [];

  for (const step of steps) {
    // 模拟 WebSocket 消息到达（无障碍下跳过等待）
    await sleep(opts.mockWsMessageGapMs);

    let id: TLShapeId;
    if (step.kind === "card") {
      id = createCardShape(editor, pageId, step.card, step.index);
    } else {
      id = createConnectorShape(editor, pageId, step.afterIndex);
    }

    createdIds.push(id);
    revealGeoShape(editor, id, opts);

    // 等待单笔入场动画大致结束后再收下一包（无障碍下极短）
    const settleMs = opts.reducedMotion ? 0 : Math.min(720, opts.shapeRevealDurationMs + 80);
    await sleep(settleMs);
  }

  editor.zoomToFit({
    animation: {
      duration: opts.reducedMotion ? 0 : 340,
      easing: opts.reducedMotion ? undefined : (t) => 1 - (1 - t) ** 2,
    },
  });
  // 双帧再 fit 一次，避免部分环境下首次 bounds 未就绪导致缩到角落「看不见」
  requestAnimationFrame(() => {
    editor.zoomToFit({
      animation: { duration: opts.reducedMotion ? 0 : 220 },
    });
  });

  return createdIds;
}

/** @deprecated 并行 RAF _burst；保留供调试，默认流程请用 streamAgentStoryboard */
export function animateGrowthBurst(
  editor: Editor,
  ids: TLShapeId[],
  opts?: { durationMs?: number; staggerMs?: number },
) {
  const durationMs = opts?.durationMs ?? 560;
  const staggerMs = opts?.staggerMs ?? 140;

  if (ids.length === 0) return Promise.resolve();

  const t0 = performance.now();

  function easeOutCubic(t: number) {
    return 1 - (1 - t) ** 3;
  }

  return Promise.all(
    ids.map(
      (id, index) =>
        new Promise<void>((resolve) => {
          const delay = index * staggerMs;

          function tick(now: number) {
            const elapsed = now - t0 - delay;
            if (elapsed < 0) {
              requestAnimationFrame(tick);
              return;
            }
            const t = Math.min(1, elapsed / durationMs);
            const e = easeOutCubic(t);
            editor.updateShapes([
              {
                id,
                type: "geo",
                opacity: e,
                props: { scale: 0.06 + e * 0.94 },
              },
            ]);
            if (t < 1) requestAnimationFrame(tick);
            else resolve();
          }

          requestAnimationFrame(tick);
        }),
    ),
  );
}

export async function runGrowthDemo(editor: Editor, cards: StoryCardSpec[], streamOpts?: Partial<StoryStreamOptions>) {
  return streamAgentStoryboard(editor, cards, streamOpts);
}
