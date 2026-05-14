"use client";

import Image from "next/image";

import { cn } from "@/components/UiPrimitives";

/** Ribbon-only squircle (transparent PNG); outer rounded box is the single frame. */
export function EkoSquircleMark({ className = "" }: { className?: string }) {
  return (
    <span className={cn("relative inline-flex shrink-0 overflow-hidden rounded-[14px] bg-transparent", className)}>
      <Image
        src="/eko-app-icon.png"
        alt=""
        width={1024}
        height={1024}
        sizes="128px"
        quality={100}
        className="h-full w-full origin-center scale-[1.06] object-contain object-center select-none"
        draggable={false}
        aria-hidden
      />
    </span>
  );
}

/** Horizontal lockup: gradient ribbon + Eko wordmark. */
export function BrandMark({ className = "" }: { className?: string }) {
  return (
    <Image
      src="/eko-lockup.png"
      alt=""
      width={560}
      height={576}
      quality={100}
      sizes="(max-width: 640px) 220px, 300px"
      className={cn("block shrink-0 object-contain object-left", className)}
      aria-hidden
    />
  );
}

export function FeishuLogo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <path d="M4 7.4c0-1 .8-1.8 1.8-1.8h6.7L8.4 13H5.8A1.8 1.8 0 0 1 4 11.2V7.4Z" fill="#1C8BFF" />
      <path d="M12.2 5.6h5.6c1 0 1.8.8 1.8 1.8v1.8a4 4 0 0 1-4 4h-5l1.6-7.6Z" fill="#35C59D" />
      <path d="M8.6 13.8h10.2a1.8 1.8 0 0 1 1.7 2.4l-.5 1.4a3.4 3.4 0 0 1-3.2 2.3H8.6V13.8Z" fill="#3558FF" />
      <path d="M5 14.2h2.7v5a1.7 1.7 0 0 1-2.7-1.3v-3.7Z" fill="#67D66E" />
    </svg>
  );
}

export function GoogleLogo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <path d="M21.6 12.2c0-.8-.1-1.4-.2-2H12v3.7h5.5a4.7 4.7 0 0 1-2 3.1v2.6h3.3c2-1.9 2.8-4.5 2.8-7.4Z" fill="#4285F4" />
      <path d="M12 22c2.7 0 5-.9 6.7-2.5l-3.3-2.6c-.9.6-2 .9-3.4.9-2.6 0-4.8-1.8-5.5-4.2H3.1v2.7A10.1 10.1 0 0 0 12 22Z" fill="#34A853" />
      <path d="M6.5 13.6a6 6 0 0 1 0-3.2V7.7H3.1a10.1 10.1 0 0 0 0 8.6l3.4-2.7Z" fill="#FBBC05" />
      <path d="M12 6.2c1.5 0 2.8.5 3.8 1.5l2.8-2.8C17 3.3 14.7 2.4 12 2.4A10.1 10.1 0 0 0 3.1 7.7l3.4 2.7c.7-2.4 2.9-4.2 5.5-4.2Z" fill="#EA4335" />
    </svg>
  );
}
