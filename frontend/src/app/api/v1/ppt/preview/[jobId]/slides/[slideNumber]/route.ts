import { svgPptSlide } from "@/lib/mock/svg-placeholders";

export const dynamic = "force-dynamic";

const SLIDE_TITLES: Record<number, string> = {
  1: "封面",
  2: "关键结论",
  3: "下一步",
};

export async function GET(_req: Request, ctx: { params: Promise<{ jobId: string; slideNumber: string }> }) {
  const { slideNumber } = await ctx.params;
  const n = Number.parseInt(slideNumber, 10);
  const safe = Number.isFinite(n) && n > 0 ? n : 1;
  const title = SLIDE_TITLES[safe] ?? `幻灯片 ${safe}`;
  const svg = svgPptSlide({ slideNumber: safe, title, subtitle: `job preview · slide ${safe}` });

  return new Response(svg, {
    status: 200,
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  });
}
