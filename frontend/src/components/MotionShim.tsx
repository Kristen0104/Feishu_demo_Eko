"use client";

import { forwardRef, type ComponentPropsWithoutRef, type ReactNode } from "react";

type MotionOnlyProps = {
  animate?: unknown;
  exit?: unknown;
  initial?: unknown;
  layout?: unknown;
  mode?: unknown;
  transition?: unknown;
  whileHover?: unknown;
  whileTap?: unknown;
};

type MotionDivProps = Omit<ComponentPropsWithoutRef<"div">, keyof MotionOnlyProps> & MotionOnlyProps;

export function AnimatePresence({ children }: { children: ReactNode; mode?: "sync" | "popLayout" | "wait" }) {
  return <>{children}</>;
}

const MotionDiv = forwardRef<HTMLDivElement, MotionDivProps>(function MotionDiv(
  { animate, exit, initial, layout, mode, transition, whileHover, whileTap, ...props },
  ref,
) {
  void animate;
  void exit;
  void initial;
  void layout;
  void mode;
  void transition;
  void whileHover;
  void whileTap;

  return <div ref={ref} {...props} />;
});

export const motion = {
  div: MotionDiv,
};
