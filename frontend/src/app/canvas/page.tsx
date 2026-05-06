import type { Metadata } from "next";
import { Suspense } from "react";

import { CanvasEntry } from "./canvas-entry";

export const metadata: Metadata = {
  title: "画布 · Eko",
  description: "创建者专属画板编辑页",
};

function CanvasFallback() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-2 bg-[#0b1020] text-sm text-white/80">
      <span className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-violet-400/30 border-t-violet-400" />
      正在加载画布…
    </div>
  );
}

export default function CanvasPage() {
  return (
    <Suspense fallback={<CanvasFallback />}>
      <CanvasEntry />
    </Suspense>
  );
}
