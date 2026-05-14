import type { Metadata } from "next";

import { CanvasEntry } from "./canvas-entry";

export const metadata: Metadata = {
  title: "画布 · Eko",
  description: "Tldraw 无限画布",
};

export default function CanvasPage() {
  return <CanvasEntry />;
}
