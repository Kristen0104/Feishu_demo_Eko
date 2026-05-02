"use client";

import { useCallback, useState } from "react";

import { AccentTone } from "@/types/workspace";

import { AtIcon, ClipIcon, EmojiIcon, SendIcon } from "./Icons";

export function MessageInput({
  tone,
  placeholder = "输入消息或 @Eko 发起任务…",
  sessionId: _sessionId,
  onSend,
  disabled,
}: {
  tone: AccentTone;
  placeholder?: string;
  /** Passed through for future analytics / correlation (same UI surface). */
  sessionId?: string;
  onSend?: (text: string) => void | Promise<void>;
  disabled?: boolean;
}) {
  void _sessionId;
  const [value, setValue] = useState("");
  const interactive = Boolean(onSend);

  const submit = useCallback(async () => {
    const trimmed = value.trim();
    if (!trimmed || !onSend || disabled) return;
    await onSend(trimmed);
    setValue("");
  }, [value, onSend, disabled]);

  return (
    <div className="rounded-[20px] border border-slate-200 bg-white px-4 py-3.5 shadow-[0_6px_16px_rgba(15,23,42,0.03)]">
      <input
        readOnly={!interactive}
        value={interactive ? value : ""}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void submit();
          }
        }}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full bg-transparent text-[14px] text-slate-900 outline-none placeholder:text-slate-400 read-only:cursor-default read-only:text-slate-400"
      />
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-3 text-slate-500">
          <EmojiIcon />
          <ClipIcon />
          <AtIcon />
        </div>
        <button
          type="button"
          onClick={() => void submit()}
          disabled={disabled || !interactive}
          className="rounded-full border border-transparent p-2 transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-40"
          aria-label="发送"
        >
          <SendIcon tone={tone} />
        </button>
      </div>
    </div>
  );
}
