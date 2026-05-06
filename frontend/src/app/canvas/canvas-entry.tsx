"use client";

import dynamic from "next/dynamic";
import { Suspense } from "react";

import "tldraw/tldraw.css";

const EkoCanvasApp = dynamic(() => import("@/components/tldraw/EkoCanvasApp").then((m) => m.EkoCanvasApp), {
  ssr: false,
  loading: () => (
    <div className="flex h-[100dvh] flex-col items-center justify-center gap-2 bg-[#0b1220] text-sm text-slate-400">
      <span className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-violet-400/30 border-t-violet-400" />
      正在加载 Tldraw 画布引擎…
    </div>
  ),
});

export function CanvasEntry() {
  return (
    <Suspense
      fallback={<div className="flex h-[100dvh] items-center justify-center bg-[#0b1220] text-sm text-slate-400">正在加载…</div>}
    >
      <EkoCanvasApp />
    </Suspense>
  );
}
