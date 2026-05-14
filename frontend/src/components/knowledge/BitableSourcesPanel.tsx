"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  createBitableSource,
  deleteBitableSource,
  getBitableDiscoveryStatus,
  inspectBitableSource,
  listBitableBases,
  listBitableFields,
  listBitableSources,
  listBitableTables,
  listBitableViews,
  queryBitableRecords,
  resolveBitableBaseUrl,
  updateBitableSource,
  type BitableBaseOption,
  type BitableDiscoveryStatus,
  type BitableFieldOption,
  type BitablePurpose,
  type BitableSource,
  type BitableTableOption,
  type BitableViewOption,
} from "@/lib/bitable-api";

const WORKSPACE_ID = "Feishu_demo_Eko";

type FieldKey = "title_field" | "summary_field" | "url_field" | "status_field" | "owner_field" | "date_field";

type SelectorDraft = {
  base_id: string;
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

type AdvancedDraft = {
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

const emptySelectorDraft: SelectorDraft = {
  base_id: "",
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

const emptyAdvancedDraft: AdvancedDraft = {
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

const fieldLabels: Record<FieldKey, string> = {
  title_field: "标题字段",
  summary_field: "摘要字段",
  url_field: "链接字段",
  status_field: "状态字段",
  owner_field: "负责人字段",
  date_field: "日期字段",
};

const autoMappingRules: Record<FieldKey, string[]> = {
  title_field: ["任务名称", "任务", "标题", "名称", "主题", "事项", "项目", "title", "name", "task"],
  summary_field: ["任务描述", "描述", "内容", "摘要", "说明", "备注", "详情", "description", "summary", "content", "note"],
  url_field: ["链接", "地址", "url", "link"],
  status_field: ["状态", "进度", "阶段", "status", "state", "progress"],
  owner_field: ["负责人", "所有者", "经办人", "成员", "owner", "assignee", "person", "member"],
  date_field: ["截止日期", "截止时间", "日期", "时间", "deadline", "due", "date", "time"],
};

function sourceStatus(source: BitableSource) {
  if (source.last_check_status === "ok") return "已连接";
  if (source.last_check_status === "failed") return "连接失败";
  return source.enabled ? "待检查" : "已停用";
}

function purposeLabel(purpose: BitablePurpose) {
  if (purpose === "context") return "仅作为素材";
  if (purpose === "archive") return "仅归档成果";
  return "素材与归档";
}

function modeCopy(status: BitableDiscoveryStatus | null) {
  if (!status) return "正在读取连接状态";
  if (!status.bound) return status.message || "未绑定飞书账号；可通过链接或手动连接添加应用可访问的表格";
  if (status.needs_reauth) return status.message || "账号授权已过期，自动发现不可用；已保存连接仍可继续读取";
  if (status.mode === "preset") return "正在使用团队预置的多维表格";
  if (status.mode === "user_oauth") return "正在使用你的飞书身份读取可访问的多维表格";
  if (status.mode === "tenant_app") return "正在使用当前应用可访问的多维表格";
  return "可通过链接或手动连接添加多维表格";
}

function optionName<T extends { id: string; name: string }>(items: T[], id: string) {
  return items.find((item) => item.id === id)?.name || "";
}

function fieldName(field: BitableFieldOption) {
  return field.name || field.id || "";
}

function clean(value: string) {
  const next = value.trim();
  return next || null;
}

function normalizeFieldName(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[\s_\-()[\]（）【】「」:：/\\|.]/g, "");
}

function autoMapFields(fields: BitableFieldOption[]): Pick<SelectorDraft, FieldKey> {
  const options = fields
    .map((field) => ({ name: fieldName(field), normalized: normalizeFieldName(fieldName(field)), type: String(field.type || "").toLowerCase() }))
    .filter((field) => field.name);
  const used = new Set<string>();

  function pick(key: FieldKey, typeHints: string[] = []) {
    const rules = autoMappingRules[key].map(normalizeFieldName);
    const exact = options.find((field) => !used.has(field.name) && rules.includes(field.normalized));
    const contains = exact || options.find((field) => !used.has(field.name) && rules.some((rule) => field.normalized.includes(rule) || rule.includes(field.normalized)));
    const typed = contains || options.find((field) => !used.has(field.name) && typeHints.some((hint) => field.type.includes(hint)));
    if (!typed) return "";
    used.add(typed.name);
    return typed.name;
  }

  return {
    title_field: pick("title_field", ["text"]),
    summary_field: pick("summary_field", ["text"]),
    url_field: pick("url_field", ["url", "link"]),
    status_field: pick("status_field", ["single", "option", "select"]),
    owner_field: pick("owner_field", ["user", "person"]),
    date_field: pick("date_field", ["date", "time"]),
  };
}

export function BitableSourcesPanel() {
  const [sources, setSources] = useState<BitableSource[]>([]);
  const [status, setStatus] = useState<BitableDiscoveryStatus | null>(null);
  const [bases, setBases] = useState<BitableBaseOption[]>([]);
  const [tables, setTables] = useState<BitableTableOption[]>([]);
  const [views, setViews] = useState<BitableViewOption[]>([]);
  const [fields, setFields] = useState<BitableFieldOption[]>([]);
  const [draft, setDraft] = useState<SelectorDraft>(emptySelectorDraft);
  const [advancedDraft, setAdvancedDraft] = useState<AdvancedDraft>(emptyAdvancedDraft);
  const [baseUrl, setBaseUrl] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [query, setQuery] = useState("项目排期 负责人 状态");
  const [queryResult, setQueryResult] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingBases, setLoadingBases] = useState(false);
  const [loadingTables, setLoadingTables] = useState(false);
  const [loadingFields, setLoadingFields] = useState(false);
  const [saving, setSaving] = useState(false);
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fieldOptions = useMemo(() => fields.map(fieldName).filter(Boolean), [fields]);
  const canUseSelectors = Boolean((status?.bound && !status.needs_reauth && status.mode !== "advanced_only") || bases.length > 0);

  useEffect(() => {
    let cancelled = false;
    async function loadInitial() {
      setLoading(true);
      setNotice(null);
      try {
        const [nextStatus, nextSources] = await Promise.all([
          getBitableDiscoveryStatus(),
          listBitableSources(WORKSPACE_ID),
        ]);
        if (cancelled) return;
        setStatus(nextStatus);
        setSources(nextSources);
        if (nextStatus.bound && !nextStatus.needs_reauth && nextStatus.mode !== "advanced_only") {
          setLoadingBases(true);
          const nextBases = await listBitableBases();
          if (!cancelled) setBases(nextBases);
        }
      } catch (error) {
        if (!cancelled) setNotice(error instanceof Error ? error.message : "加载 Bitable 配置失败");
      } finally {
        if (!cancelled) {
          setLoading(false);
          setLoadingBases(false);
        }
      }
    }

    void loadInitial();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshSources() {
    setSources(await listBitableSources(WORKSPACE_ID));
  }

  async function handleBaseChange(baseId: string) {
    setDraft((current) => ({
      ...current,
      base_id: baseId,
      table_id: "",
      view_id: "",
      title_field: "",
      summary_field: "",
      url_field: "",
      status_field: "",
      owner_field: "",
      date_field: "",
    }));
    setTables([]);
    setViews([]);
    setFields([]);
    if (!baseId) return;

    setLoadingTables(true);
    setNotice(null);
    try {
      setTables(await listBitableTables(baseId));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "加载数据表失败");
    } finally {
      setLoadingTables(false);
    }
  }

  async function handleResolveBaseUrl() {
    if (!baseUrl.trim()) {
      setNotice("请粘贴飞书多维表格链接。");
      return;
    }

    setLoadingTables(true);
    setNotice(null);
    try {
      const result = await resolveBitableBaseUrl(baseUrl.trim());
      setBases((current) => {
        const exists = current.some((item) => item.id === result.base.id);
        return exists ? current : [result.base, ...current];
      });
      setDraft((current) => ({
        ...current,
        base_id: result.base.id,
        table_id: "",
        view_id: result.view_id || "",
        title_field: "",
        summary_field: "",
        url_field: "",
        status_field: "",
        owner_field: "",
        date_field: "",
      }));
      setViews([]);
      setFields([]);
      const nextTables = await listBitableTables(result.base.id);
      setTables(nextTables);
      const tableId = result.table_id && nextTables.some((table) => table.id === result.table_id)
        ? result.table_id
        : nextTables[0]?.id || "";
      if (tableId) {
        await handleTableChangeWithBase(result.base.id, tableId, result.view_id || "");
      }
      setNotice("已识别多维表格链接，请确认数据表和字段映射。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "识别多维表格链接失败");
    } finally {
      setLoadingTables(false);
    }
  }

  async function handleTableChangeWithBase(baseId: string, tableId: string, preferredViewId = "") {
    setDraft((current) => ({
      ...current,
      base_id: baseId,
      table_id: tableId,
      view_id: preferredViewId,
      title_field: "",
      summary_field: "",
      url_field: "",
      status_field: "",
      owner_field: "",
      date_field: "",
    }));
    setViews([]);
    setFields([]);
    if (!baseId || !tableId) return;

    setLoadingFields(true);
    setNotice(null);
    try {
      const [nextViews, nextFields] = await Promise.all([
        listBitableViews(baseId, tableId),
        listBitableFields(baseId, tableId),
      ]);
      const autoMapping = autoMapFields(nextFields);
      setViews(nextViews);
      setFields(nextFields);
      setDraft((current) => ({
        ...current,
        view_id: preferredViewId && nextViews.some((view) => view.id === preferredViewId)
          ? preferredViewId
          : nextViews[0]?.id || "",
        ...autoMapping,
      }));
      const mappedCount = Object.values(autoMapping).filter(Boolean).length;
      if (mappedCount > 0) {
        setNotice(`已自动映射 ${mappedCount} 个字段，可直接保存或手动调整。`);
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "加载视图或字段失败");
    } finally {
      setLoadingFields(false);
    }
  }

  async function handleTableChange(tableId: string) {
    setDraft((current) => ({
      ...current,
      table_id: tableId,
      view_id: "",
      title_field: "",
      summary_field: "",
      url_field: "",
      status_field: "",
      owner_field: "",
      date_field: "",
    }));
    setViews([]);
    setFields([]);
    if (!draft.base_id || !tableId) return;

    setLoadingFields(true);
    setNotice(null);
    try {
      await handleTableChangeWithBase(draft.base_id, tableId);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "加载视图或字段失败");
    } finally {
      setLoadingFields(false);
    }
  }

  async function handleCreateFromSelector() {
    if (!draft.base_id || !draft.table_id) {
      setNotice("请选择多维表格和数据表。");
      return;
    }

    const baseName = optionName(bases, draft.base_id) || "多维表格";
    const tableName = optionName(tables, draft.table_id) || "数据表";
    setSaving(true);
    setNotice(null);
    try {
      const created = await createBitableSource({
        workspace_id: WORKSPACE_ID,
        name: `${baseName} / ${tableName}`,
        base_id: draft.base_id,
        table_id: draft.table_id,
        view_id: clean(draft.view_id),
        purpose: draft.purpose,
        title_field: clean(draft.title_field),
        summary_field: clean(draft.summary_field),
        url_field: clean(draft.url_field),
        status_field: clean(draft.status_field),
        owner_field: clean(draft.owner_field),
        date_field: clean(draft.date_field),
        field_mapping: {},
      });
      setSources((current) => [created, ...current]);
      setDraft(emptySelectorDraft);
      setTables([]);
      setViews([]);
      setFields([]);
      setNotice("已连接多维表格，可立即检查或用于创作。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateAdvanced() {
    if (!advancedDraft.name.trim() || !advancedDraft.app_token.trim() || !advancedDraft.table_id.trim()) {
      setNotice("请填写手动连接中的名称、App Token 和 Table ID。");
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      const created = await createBitableSource({
        workspace_id: WORKSPACE_ID,
        name: advancedDraft.name.trim(),
        app_token: advancedDraft.app_token.trim(),
        table_id: advancedDraft.table_id.trim(),
        view_id: clean(advancedDraft.view_id),
        purpose: advancedDraft.purpose,
        title_field: clean(advancedDraft.title_field),
        summary_field: clean(advancedDraft.summary_field),
        url_field: clean(advancedDraft.url_field),
        status_field: clean(advancedDraft.status_field),
        owner_field: clean(advancedDraft.owner_field),
        date_field: clean(advancedDraft.date_field),
        field_mapping: {},
      });
      setSources((current) => [created, ...current]);
      setAdvancedDraft(emptyAdvancedDraft);
      setNotice("已保存手动连接，可立即检查或用于创作。");
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
        setQueryResult(result.failures.length ? `未命中记录；${result.failures.length} 个连接读取失败，请检查应用权限或表格配置。` : "未命中记录。");
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

  function updateDraft<K extends keyof SelectorDraft>(key: K, value: SelectorDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function updateAdvanced<K extends keyof AdvancedDraft>(key: K, value: AdvancedDraft[K]) {
    setAdvancedDraft((current) => ({ ...current, [key]: value }));
  }

  function handleAutoMapFields() {
    const autoMapping = autoMapFields(fields);
    const mappedCount = Object.values(autoMapping).filter(Boolean).length;
    setDraft((current) => ({ ...current, ...autoMapping }));
    setNotice(mappedCount > 0 ? `已自动映射 ${mappedCount} 个字段。` : "没有找到可自动映射的字段。");
  }

  return (
    <section className="rounded-[16px] border border-slate-200 bg-white p-3 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-[18px] font-semibold text-slate-950">多维表格</h2>
          <p className="mt-1 max-w-[720px] text-[13px] leading-6 text-slate-500">
            从已连接的多维表格读取结构化素材，并把正式成果归档到你选择的表格。
          </p>
        </div>
        <span className="inline-flex h-8 items-center rounded-[10px] border border-slate-200 px-3 text-[12px] font-semibold text-slate-600">
          {loading ? "加载中" : `${sources.length} 个配置`}
        </span>
      </div>

      <div className="mt-4 rounded-[12px] border border-slate-200 bg-slate-50 px-4 py-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[13px] font-medium leading-5 text-slate-700">{modeCopy(status)}</p>
          {status && (!status.bound || status.needs_reauth) ? (
            <Link href="/login/feishu/start?mode=bind" className="inline-flex h-9 items-center justify-center rounded-[10px] bg-slate-950 px-3 text-[13px] font-semibold text-white transition hover:bg-slate-800 active:translate-y-px">
              授权飞书
            </Link>
          ) : null}
        </div>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.12fr)_minmax(340px,0.88fr)]">
        <div className="rounded-[14px] border border-slate-200 bg-slate-50/60 p-4">
          <div className="mb-4 rounded-[12px] border border-slate-200 bg-white p-3">
            <label className="block">
              <span className="text-[12px] font-semibold text-slate-700">飞书多维表格链接</span>
              <div className="mt-1 flex flex-col gap-2 sm:flex-row">
                <input
                  value={baseUrl}
                  onChange={(event) => setBaseUrl(event.target.value)}
                  className="h-10 min-w-0 flex-1 rounded-[11px] border border-slate-200 px-3 text-[13px] outline-none focus:border-blue-500"
                  placeholder="https://...feishu.cn/base/..."
                />
                <button
                  type="button"
                  onClick={() => void handleResolveBaseUrl()}
                  disabled={loadingTables}
                  className="h-10 rounded-[11px] bg-blue-600 px-4 text-[13px] font-semibold text-white transition hover:bg-blue-700 active:translate-y-px disabled:bg-slate-300"
                >
                  {loadingTables ? "识别中..." : "识别链接"}
                </button>
              </div>
            </label>
          </div>

          {canUseSelectors ? (
            <>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="block">
                  <span className="text-[12px] font-semibold text-slate-700">多维表格</span>
                  <select value={draft.base_id} onChange={(event) => void handleBaseChange(event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-500" disabled={loadingBases}>
                    <option value="">{loadingBases ? "正在加载" : "请选择"}</option>
                    {bases.map((base) => (
                      <option key={base.id} value={base.id}>{base.name}</option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="text-[12px] font-semibold text-slate-700">数据表</span>
                  <select value={draft.table_id} onChange={(event) => void handleTableChange(event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-500" disabled={!draft.base_id || loadingTables}>
                    <option value="">{loadingTables ? "正在加载" : "请选择"}</option>
                    {tables.map((table) => (
                      <option key={table.id} value={table.id}>{table.name}</option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="text-[12px] font-semibold text-slate-700">视图</span>
                  <select value={draft.view_id} onChange={(event) => updateDraft("view_id", event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-500" disabled={!draft.table_id || loadingFields}>
                    <option value="">{loadingFields ? "正在加载" : "全部记录"}</option>
                    {views.map((view) => (
                      <option key={view.id} value={view.id}>{view.name}</option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="text-[12px] font-semibold text-slate-700">用途</span>
                  <select value={draft.purpose} onChange={(event) => updateDraft("purpose", event.target.value as BitablePurpose)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-500">
                    <option value="both">素材与归档</option>
                    <option value="context">仅作为素材</option>
                    <option value="archive">仅归档成果</option>
                  </select>
                </label>
              </div>

              {fields.length ? (
                <div className="mt-4 rounded-[12px] border border-slate-200 bg-white p-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-[12px] font-semibold text-slate-700">字段映射</p>
                    <button type="button" onClick={handleAutoMapFields} className="h-8 rounded-[9px] border border-slate-200 px-3 text-[12px] font-semibold text-slate-700 transition hover:bg-slate-50">
                      重新自动映射
                    </button>
                  </div>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    {(Object.keys(fieldLabels) as FieldKey[]).map((key) => (
                      draft[key] ? (
                        <div key={key} className="flex min-w-0 items-center justify-between gap-3 rounded-[10px] bg-slate-50 px-3 py-2">
                          <span className="shrink-0 text-[12px] font-semibold text-slate-600">{fieldLabels[key]}</span>
                          <span className="min-w-0 truncate text-right text-[12px] font-medium text-slate-900">{draft[key]}</span>
                        </div>
                      ) : null
                    ))}
                  </div>
                  <details className="mt-3">
                    <summary className="cursor-pointer text-[12px] font-semibold text-slate-500">手动调整字段</summary>
                    <div className="mt-3 grid gap-3 md:grid-cols-3">
                      {(Object.keys(fieldLabels) as FieldKey[]).map((key) => (
                        <label key={key} className="block">
                          <span className="text-[12px] font-semibold text-slate-700">{fieldLabels[key]}</span>
                          <select value={draft[key]} onChange={(event) => updateDraft(key, event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-500">
                            <option value="">不映射</option>
                            {fieldOptions.map((name) => (
                              <option key={`${key}-${name}`} value={name}>{name}</option>
                            ))}
                          </select>
                        </label>
                      ))}
                    </div>
                  </details>
                </div>
              ) : null}

              <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
                <button type="button" onClick={() => void handleCreateFromSelector()} disabled={saving || !draft.base_id || !draft.table_id} className="inline-flex h-10 w-full items-center justify-center rounded-[11px] bg-slate-950 px-4 text-[13px] font-semibold text-white transition hover:bg-slate-800 active:translate-y-px disabled:bg-slate-300 sm:w-auto">
                  {saving ? "保存中..." : "保存连接"}
                </button>
                {notice ? <p className="text-[13px] leading-5 text-slate-600">{notice}</p> : null}
              </div>
            </>
          ) : (
            <div className="rounded-[12px] border border-dashed border-slate-300 bg-white px-4 py-6">
              <p className="text-[14px] font-semibold text-slate-900">当前无法自动列出你的多维表格</p>
              <p className="mt-2 max-w-[560px] text-[13px] leading-6 text-slate-500">
                已保存的连接仍会参与检索；新增表格可粘贴链接识别，或使用下方手动连接填写 App Token 和 Table ID。
              </p>
              <Link href="/login/feishu/start?mode=bind" className="mt-4 inline-flex h-10 w-full items-center justify-center rounded-[11px] bg-slate-950 px-4 text-[13px] font-semibold text-white transition hover:bg-slate-800 active:translate-y-px sm:w-auto">
                授权飞书后自动选择
              </Link>
            </div>
          )}

          <div className="mt-4 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => setAdvancedOpen((current) => !current)} className="inline-flex h-9 items-center rounded-[10px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 transition hover:bg-slate-50">
              手动连接
              <span className="ml-2 text-slate-400">用于无法自动授权的环境</span>
            </button>

            {advancedOpen ? (
              <div className="mt-3 rounded-[12px] border border-slate-200 bg-white p-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="block">
                    <span className="text-[12px] font-semibold text-slate-700">名称</span>
                    <input value={advancedDraft.name} onChange={(event) => updateAdvanced("name", event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 px-3 text-[13px] outline-none focus:border-blue-500" placeholder="项目资料表" />
                  </label>
                  <label className="block">
                    <span className="text-[12px] font-semibold text-slate-700">用途</span>
                    <select value={advancedDraft.purpose} onChange={(event) => updateAdvanced("purpose", event.target.value as BitablePurpose)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 bg-white px-3 text-[13px] outline-none focus:border-blue-500">
                      <option value="both">素材与归档</option>
                      <option value="context">仅作为素材</option>
                      <option value="archive">仅归档成果</option>
                    </select>
                  </label>
                  <label className="block md:col-span-2">
                    <span className="text-[12px] font-semibold text-slate-700">App Token</span>
                    <input value={advancedDraft.app_token} onChange={(event) => updateAdvanced("app_token", event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 px-3 text-[13px] outline-none focus:border-blue-500" />
                  </label>
                  <label className="block">
                    <span className="text-[12px] font-semibold text-slate-700">Table ID</span>
                    <input value={advancedDraft.table_id} onChange={(event) => updateAdvanced("table_id", event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 px-3 text-[13px] outline-none focus:border-blue-500" />
                  </label>
                  <label className="block">
                    <span className="text-[12px] font-semibold text-slate-700">View ID</span>
                    <input value={advancedDraft.view_id} onChange={(event) => updateAdvanced("view_id", event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 px-3 text-[13px] outline-none focus:border-blue-500" placeholder="可选" />
                  </label>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  {(Object.keys(fieldLabels) as FieldKey[]).map((key) => (
                    <label key={key} className="block">
                      <span className="text-[12px] font-semibold text-slate-700">{fieldLabels[key]}</span>
                      <input value={advancedDraft[key]} onChange={(event) => updateAdvanced(key, event.target.value)} className="mt-1 h-10 w-full rounded-[11px] border border-slate-200 px-3 text-[13px] outline-none focus:border-blue-500" placeholder="字段名称" />
                    </label>
                  ))}
                </div>
                <button type="button" onClick={() => void handleCreateAdvanced()} disabled={saving} className="mt-4 inline-flex h-10 w-full items-center justify-center rounded-[11px] bg-slate-950 px-4 text-[13px] font-semibold text-white transition hover:bg-slate-800 active:translate-y-px disabled:bg-slate-300 sm:w-auto">
                  {saving ? "保存中..." : "保存手动连接"}
                </button>
              </div>
            ) : null}
          </div>
        </div>

        <div className="rounded-[14px] border border-slate-200 bg-white p-4">
          <h3 className="text-[14px] font-semibold text-slate-950">已配置</h3>
          <div className="mt-3 max-h-[394px] space-y-2 overflow-y-auto pr-1">
            {!loading && sources.length === 0 ? <p className="text-[13px] text-slate-500">还没有多维表格连接。</p> : null}
            {sources.map((source) => (
              <article key={source.id} className="rounded-[13px] border border-slate-200 px-3 py-2.5">
                <div className="flex min-w-0 items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-semibold text-slate-900">{source.name}</p>
                    <p className="mt-1 text-[12px] text-slate-500">{purposeLabel(source.purpose)} · {sourceStatus(source)}</p>
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
          <h3 className="text-[14px] font-semibold text-slate-950">字段映射预览</h3>
          <div className="mt-3 max-h-[220px] overflow-y-auto rounded-[12px] bg-slate-50 p-3">
            {fields.length === 0 ? <p className="text-[13px] text-slate-500">选择数据表后展示字段。</p> : null}
            {fields.map((field) => (
              <div key={field.id || field.name} className="flex items-center justify-between gap-3 border-b border-slate-200/70 py-2 last:border-b-0">
                <span className="truncate text-[13px] font-medium text-slate-800">{field.name}</span>
                <span className="shrink-0 text-[12px] text-slate-500">{String(field.type || "field")}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[14px] border border-slate-200 bg-white p-4">
          <h3 className="text-[14px] font-semibold text-slate-950">查询验证</h3>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="h-10 min-w-0 flex-1 rounded-[11px] border border-slate-200 px-3 text-[13px] outline-none focus:border-blue-500" />
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
