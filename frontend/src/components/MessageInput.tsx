import { AccentTone } from "@/types/workspace";

import { AtIcon, ClipIcon, EmojiIcon, SendIcon } from "./Icons";

export function MessageInput({ tone, placeholder = "输入消息或 @Eko 发起任务..." }: { tone: AccentTone; placeholder?: string; }) {
  return (
    <div className="rounded-[20px] border border-slate-200 bg-white px-4 py-3.5 shadow-[0_6px_16px_rgba(15,23,42,0.03)]">
      <input readOnly value="" placeholder={placeholder} className="w-full bg-transparent text-[14px] text-slate-400 outline-none placeholder:text-slate-400" />
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-3 text-slate-500"><EmojiIcon /><ClipIcon /><AtIcon /></div>
        <button type="button" className="rounded-full border border-transparent p-2 transition hover:bg-slate-50" aria-label="发送"><SendIcon tone={tone} /></button>
      </div>
    </div>
  );
}
