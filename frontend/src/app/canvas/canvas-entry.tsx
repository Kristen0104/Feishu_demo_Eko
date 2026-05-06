"use client";

import { Suspense } from "react";

import "tldraw/tldraw.css";

import { EkoCanvasApp } from "@/components/tldraw/EkoCanvasApp";

export function CanvasEntry() {
  return (
    <Suspense
      fallback={<div className="flex h-[100dvh] items-center justify-center bg-[#0b1220] text-sm text-slate-400">正在加载…</div>}
    >
      <EkoCanvasApp />
    </Suspense>
  );
}
