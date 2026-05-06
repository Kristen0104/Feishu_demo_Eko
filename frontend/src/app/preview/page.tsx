import type { Metadata } from "next";
import { Suspense } from "react";

import { EkoWorkspace } from "@/components/collab/EkoWorkspace";

export const metadata: Metadata = {
  title: "预览 · Eko",
  description: "全员观摩预览页",
};

function PreviewFallback() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-2 bg-[#0b1020] text-sm text-white/80">
      <span className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-violet-400/30 border-t-violet-400" />
      正在加载预览…
    </div>
  );
}

export default function PreviewPage() {
  return (
    <Suspense fallback={<PreviewFallback />}>
      <EkoWorkspace mode="preview" />
    </Suspense>
  );
}
