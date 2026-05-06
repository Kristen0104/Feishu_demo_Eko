import { svgBoardPreview } from "@/lib/mock/svg-placeholders";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const wb = url.searchParams.get("wb") ?? "demo";
  const svg = svgBoardPreview({ label: `whiteboard: ${wb}` });
  return new Response(svg, {
    status: 200,
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  });
}
