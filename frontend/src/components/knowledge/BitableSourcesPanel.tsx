"use client";

import { useEffect, useMemo, useState } from "react";

import {
  createBitableSource,
  deleteBitableSource,
  inspectBitableSource,
  listBitableSources,
  queryBitableRecords,
  updateBitableSource,
  type BitableField,
  type BitablePurpose,
  type BitableSource,
} from "@/lib/bitable-api";

const WORKSPACE_ID = "Feishu_demo_Eko";

type BitableDraft = {
  name: string;
  app_token: string;
  table_id: string;
  view_id: string;
  purpose: BitablePurpose;
  title_field: string;
  summary_field: string;
  url_field: string;
  status_field: string;
  owner_field: string;
  date_field: string;
};

const emptyDraft: BitableDraft = {
  name: "",
  app_token: "",
  table_id: "",
  view_id: "",
  purpose: "both",
  title_field: "",
  summary_field: "",
  url_field: "",
  status_field: "",
  owner_field: "",
  date_field: "",
};

function fieldName(field: BitableField) {
  return String(field.field_name || field.name || field.field_id || "");
}

function sourceStatus(source: BitableSource) {
  if (source.last_check_status === "ok") return "已连接";
  if (source.last_check_status === "failed") return "连接失败";
  return source.enabled ? "待检查" : "已停用";
}

function purposeLabel(purpose: BitablePurpose) {
  if (purpose === "context") return "上下文";
  if (purpose === "archive") return "归档";
  return "上下文与归档";
}

export function BitableSourcesPanel() {
  const [sources, setSources] = useState<BitableSource[]>([]);
  const [draft, setDraft] = useState<BitableDraft>(emptyDraft);
  const [fields, setFields] = useState<BitableField[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [query, setQuery] = useState("项目排期 负责人 状态");
  const [queryResult, setQueryResult] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fieldOptions = useMemo(() => fields.map(fieldName).filter(Boolean), [fields]);

  async function refresh() {
    setLoading(true);
    try {
      setSources(await listBitableSources(WORKSPACE_ID));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "加载 Bitable 数据源失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    listBitableSources(WORKSPACE_ID)
      .then((items) => {
        if (!cancelled) setSources(items);
      })
      .catch((error) => {
        if (!cancelled) setNotice(error instanceof Error ? error.message : "加载 Bitable 数据源失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreate() {
    if (!draft.name.trim() || !draft.app_token.trim() || !draft.table_id.trim()) {
      setNotice("请填写名称、app_token 和 table_id。");
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      const created = await createBitableSource({
        workspace_id: WORKSPACE_ID,
        name: draft.name.trim(),
        app_token: draft.app_token.trim(),
        table_id: draft.table_id.trim(),
        view_id: draft.view_id.trim() || null,
        purpose: draft.purpose,
        title_field: draft.title_field.trim() || null,
        summary_field: draft.summary_field.trim() || null,
        url_field: draft.url_field.trim() || null,
        status_field: draft.status_field.trim() || null,
        owner_field: draft.owner_field.trim() || null,
        date_field: draft.date_field.trim() || null,
        field_mapping: {},
      });
      setSources((current) => [created, ...current]);
      setDraft(emptyDraft);
      setNotice("已新增 Bitable source，可立即检查连接。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "新增失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleInspect(source: BitableSource) {
    setCheckingId(source.id);
    setNotice(null);
    try {
      const result = await inspectBitableSource(source.id);
      setFields(result.fields);
      setSelectedSourceId(source.id);
      setSources((current) => current.map((item) => (item.id === source.id ? result.source : item)));
      setNotice(`已读取 ${result.fields.length} 个字段、${result.views.length} 个视图。`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "检查连接失败");
    } finally {
      setCheckingId(null);
    }
  }

  async function handleToggle(source: BitableSource) {
    try {
      const updated = await updateBitableSource(source.id, { enabled: !source.enabled });
      setSources((current) => current.map((item) => (item.id === source.id ? updated : item)));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "更新失败");
    }
  }

  async function handleDelete(source: BitableSource) {
    try {
      await deleteBitableSource(source.id);
      setSources((current) => current.filter((item) => item.id !== source.id));
      if (selectedSourceId === source.id) {
        setSelectedSourceId(null);
        setFields([]);
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "删除失败");
    }
  }

  async function handleQuery() {
    if (!query.trim()) return;
    setQueryResult("检索中...");
    try {
      const result = await queryBitableRecords(query.trim(), 5, WORKSPACE_ID);
      if (!result.records.length) {
        setQueryResult(result.failures.length ? `未命中记录；失败 ${result.failures.length} 个 source。` : "未命中记录。");
        return;
      }
      setQueryResult(
        result.records
          .map((record) => `${record.title} (${Math.round(record.score * 100)}%)\n${record.content}`)
          .join("\n\n"),
      );
    } catch (error) {
      setQueryResult(error instanceof Error ? error.message : "查询失败");
    }
  }

  function updateDraft<K extends keyof BitableDraft>(key: K, value: BitableDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  return (
    <section className="rounded-[16px] border border-slate-200 bg-white p-5 shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-[18px] font-semibold text-slate-950">Bitable 数据源</h2>
          <p className="mt-1 max-w-[720px] text-[13px] leading-6 text-slate-500">
            使用飞书官方 lark-cli Base skill 读取结构化记录，并把生成结果归档回多维表格。
          </p>
        </div>
        <span className="inline-flex h-8 items-center rounded-[10px] border border-slate-200 px-3 text-[12px] font-semibold text-slate-600">
          {loading ? "加载中" : `${sources.length} sources`}
        </span>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <div className="rounded-[14px] border border-slate-200 bg-slate-50/60 p-4">
          <div className="grid gap-3 md:grid-cols-2">
            <label className="block">
              <span className="text-[12px] font-semibold text-slate-700">名称</span>
              <input value={draft.name} onChange={(event) => updateDraft("name", event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-400" placeholder="项目资料表" />
            </label>
            <label className="block">
              <span className="text-[12px] font-semibold text-slate-700">用途</span>
              <select value={draft.purpose} onChange={(event) => updateDraft("purpose", event.target.value as BitablePurpose)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-400">
                <option value="both">上下文与归档</option>
                <option value="context">仅上下文</option>
                <option value="archive">仅归档</option>
              </select>
            </label>
            <label className="block md:col-span-2">
              <span className="text-[12px] font-semibold text-slate-700">app_token / base_token</span>
              <input value={draft.app_token} onChange={(event) => updateDraft("app_token", event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-400" placeholder="app_xxx 或 base 链接中的 token" />
            </label>
            <label className="block">
              <span className="text-[12px] font-semibold text-slate-700">table_id</span>
              <input value={draft.table_id} onChange={(event) => updateDraft("table_id", event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-400" placeholder="tbl_xxx" />
            </label>
            <label className="block">
              <span className="text-[12px] font-semibold text-slate-700">view_id</span>
              <input value={draft.view_id} onChange={(event) => updateDraft("view_id", event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-400" placeholder="可选" />
            </label>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {(["title_field", "summary_field", "url_field", "status_field", "owner_field", "date_field"] as const).map((key) => (
              <label key={key} className="block">
                <span className="text-[12px] font-semibold text-slate-700">
                  {key === "title_field" ? "标题字段" : key === "summary_field" ? "摘要字段" : key === "url_field" ? "链接字段" : key === "status_field" ? "状态字段" : key === "owner_field" ? "负责人字段" : "日期字段"}
                </span>
                <input
                  list="bitable-field-options"
                  value={draft[key]}
                  onChange={(event) => updateDraft(key, event.target.value)}
                  className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-400"
                  placeholder="字段名"
                />
              </label>
            ))}
            <datalist id="bitable-field-options">
              {fieldOptions.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>
          </div>

          <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
            <button type="button" onClick={() => void handleCreate()} disabled={saving} className="inline-flex h-10 items-center justify-center rounded-[11px] bg-slate-950 px-4 text-[13px] font-semibold text-white transition hover:bg-slate-800 active:translate-y-px disabled:bg-slate-300">
              {saving ? "保存中..." : "新增 Source"}
            </button>
            {notice ? <p className="text-[13px] leading-5 text-slate-600">{notice}</p> : null}
          </div>
        </div>

        <div className="rounded-[14px] border border-slate-200 bg-white p-4">
          <h3 className="text-[14px] font-semibold text-slate-950">已配置</h3>
          <div className="mt-3 max-h-[328px] space-y-2 overflow-y-auto pr-1">
            {!loading && sources.length === 0 ? <p className="text-[13px] text-slate-500">还没有 Bitable source。</p> : null}
            {sources.map((source) => (
              <article key={source.id} className="rounded-[13px] border border-slate-200 px-3 py-2.5">
                <div className="flex min-w-0 items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-semibold text-slate-900">{source.name}</p>
                    <p className="mt-1 text-[12px] text-slate-500">{source.table_id} · {purposeLabel(source.purpose)} · {sourceStatus(source)}</p>
                    {source.last_check_error ? <p className="mt-1 line-clamp-2 text-[12px] text-rose-600">{source.last_check_error}</p> : null}
                  </div>
                  <span className={`mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full ${source.enabled ? "bg-emerald-500" : "bg-slate-300"}`} />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={() => void handleInspect(source)} disabled={checkingId === source.id} className="h-8 rounded-[9px] bg-blue-50 px-3 text-[12px] font-semibold text-blue-700 transition hover:bg-blue-100 disabled:text-blue-300">
                    {checkingId === source.id ? "检查中" : "检查"}
                  </button>
                  <button type="button" onClick={() => void handleToggle(source)} className="h-8 rounded-[9px] bg-slate-100 px-3 text-[12px] font-semibold text-slate-700 transition hover:bg-slate-200">
                    {source.enabled ? "停用" : "启用"}
                  </button>
                  <button type="button" onClick={() => void handleDelete(source)} className="h-8 rounded-[9px] bg-rose-50 px-3 text-[12px] font-semibold text-rose-600 transition hover:bg-rose-100">
                    删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div className="rounded-[14px] border border-slate-200 bg-white p-4">
          <h3 className="text-[14px] font-semibold text-slate-950">字段快照</h3>
          <div className="mt-3 max-h-[220px] overflow-y-auto rounded-[12px] bg-slate-50 p-3">
            {fields.length === 0 ? <p className="text-[13px] text-slate-500">检查 source 后展示字段。</p> : null}
            {fields.map((field) => (
              <div key={field.field_id || fieldName(field)} className="flex items-center justify-between gap-3 border-b border-slate-200/70 py-2 last:border-b-0">
                <span className="truncate text-[13px] font-medium text-slate-800">{fieldName(field)}</span>
                <span className="shrink-0 text-[12px] text-slate-500">{String(field.type || "field")}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[14px] border border-slate-200 bg-white p-4">
          <h3 className="text-[14px] font-semibold text-slate-950">查询验证</h3>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="h-10 min-w-0 flex-1 rounded-[11px] border border-slate-200 px-3 text-[13px] outline-none focus:border-blue-400" />
            <button type="button" onClick={() => void handleQuery()} className="h-10 rounded-[11px] bg-blue-600 px-4 text-[13px] font-semibold text-white transition hover:bg-blue-700 active:translate-y-px">
              查询
            </button>
          </div>
          <pre className="mt-3 max-h-[180px] overflow-y-auto whitespace-pre-wrap rounded-[12px] bg-slate-50 p-3 text-[12px] leading-5 text-slate-600">
            {queryResult || "检索结果会显示在这里。"}
          </pre>
        </div>
      </div>
    </section>
  );
}
