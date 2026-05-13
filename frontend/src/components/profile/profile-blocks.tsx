"use client";

import { useState } from "react";

export function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[20px] border border-white/80 bg-white/95 shadow-[0_16px_48px_rgba(15,23,42,0.06)] backdrop-blur-sm sm:rounded-[24px]">
      <div className="border-b border-slate-100 px-4 py-4 sm:px-6 sm:py-5">
        <h2 className="text-[17px] font-semibold tracking-[-0.03em] text-slate-950">{title}</h2>
        {description ? <p className="mt-1 text-[13px] text-slate-500">{description}</p> : null}
      </div>
      <div className="px-4 pb-2 pt-1 sm:px-6">{children}</div>
    </section>
  );
}

export function EditableTextRow({
  label,
  value,
  hint,
  multiline,
  onSave,
}: {
  label: string;
  value: string;
  hint?: string;
  multiline?: boolean;
  onSave: (next: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const displayValue = value || "—";

  return (
    <div className="flex flex-col gap-1 border-b border-slate-100 py-4 last:border-b-0 sm:flex-row sm:items-start sm:justify-between sm:gap-8">
      <div className="w-full shrink-0 text-[13px] font-medium text-slate-500 sm:w-[168px]">{label}</div>
      <div className="min-w-0 flex-1">
        {!editing ? (
          <div key={displayValue} className="rounded-[12px] px-0 py-1 sm:px-3 sm:py-2">
            <p className="break-words whitespace-pre-wrap text-[15px] leading-[1.6] font-medium text-slate-900">{displayValue}</p>
          </div>
        ) : multiline ? (
          <textarea
            className="min-h-[88px] w-full resize-y rounded-[12px] border border-slate-200 bg-white px-3 py-2 text-[15px] text-slate-900 outline-none ring-blue-500/30 focus:ring-2"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        ) : (
          <input
            type="text"
            className="w-full rounded-[12px] border border-slate-200 bg-white px-3 py-2 text-[15px] text-slate-900 outline-none ring-blue-500/30 focus:ring-2"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        )}
        {hint ? <p className="mt-1 text-[12px] text-slate-400">{hint}</p> : null}
      </div>
      <div className="flex shrink-0 flex-row items-center justify-end gap-3 sm:gap-2">
        {!editing ? (
          <button
            type="button"
            className="text-[13px] font-semibold text-blue-500 hover:text-blue-600"
            onClick={() => {
              setDraft(value);
              setEditing(true);
            }}
          >
            编辑
          </button>
        ) : (
          <>
            <button
              type="button"
              className="rounded-[10px] bg-blue-600 px-3 py-1.5 text-[13px] font-semibold text-white hover:bg-blue-700"
              onClick={() => {
                onSave(draft);
                setEditing(false);
              }}
            >
              保存
            </button>
            <button
              type="button"
              className="text-[13px] font-semibold text-slate-500 hover:text-slate-700"
              onClick={() => {
                setDraft(value);
                setEditing(false);
              }}
            >
              取消
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div className="flex flex-col gap-2 border-b border-slate-100 py-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 flex-1">
        <p className="text-[15px] font-medium text-slate-900">{label}</p>
        {description ? <p className="mt-1 text-[13px] text-slate-500">{description}</p> : null}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-8 w-[52px] shrink-0 rounded-full transition-colors ${
          checked ? "bg-blue-600" : "bg-slate-200"
        }`}
      >
        <span
          className={`absolute top-1 left-1 h-6 w-6 rounded-full bg-white shadow transition-transform ${
            checked ? "translate-x-[22px]" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}
