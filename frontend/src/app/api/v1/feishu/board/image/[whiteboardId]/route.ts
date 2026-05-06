import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, ctx: { params: Promise<{ whiteboardId: string }> }) {
  const { whiteboardId } = await ctx.params;
  const id = decodeURIComponent(whiteboardId);
  const previewUrl = `/api/v1/mock/board/preview?wb=${encodeURIComponent(id)}`;
  return NextResponse.json({
    code: 0,
    message: "ok",
    data: {
      whiteboard_id: id,
      preview_url: previewUrl,
    },
  });
}
