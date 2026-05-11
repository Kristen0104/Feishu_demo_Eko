"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { BitableSourcesPanel } from "@/components/knowledge/BitableSourcesPanel";
import {
  deleteRagFile,
  getRagFileContent,
  listRagFiles,
  searchRag,
  updateRagFile,
  uploadRagFile,
  type RagFile,
  type RagFileContent,
  type RagSearchResult,
} from "@/lib/rag-api";

const SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".md", ".txt", ".json", ".csv", ".log"];

type KnowledgeSection = "rag" | "bitable";

type EditDraft = {
  filename: string;
  source: string;
  note: string;
  content: string;
  originalContent: string;
};

const EMPTY_DRAFT: EditDraft = {
  filename: "",
  source: "",
  note: "",
  content: "",
  originalContent: "",
};

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function shortText(text: string, max = 180) {
  const normalized = text.replace(/\s+/g, " ").trim();
  return normalized.length > max ? `${normalized.slice(0, max)}...` : normalized;
}

function formatDate(value?: string | null) {
  if (!value) return "未知时间";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function noteFromMetadata(metadata: Record<string, unknown>) {
  return typeof metadata.note === "string" ? metadata.note : "";
}

function KnowledgeIcon({ active }: { active: boolean }) {
  const stroke = active ? "#2563EB" : "#64748B";
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" fill="none" aria-hidden>
      <path d="M5.2 3.5h7.9A1.9 1.9 0 0 1 15 5.4v10.1H6.1A1.9 1.9 0 0 1 4.2 13.6V4.5a1 1 0 0 1 1-1Z" stroke={stroke} strokeWidth="1.5" />
      <path d="M7.2 7h5.1M7.2 10h4.2" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
      <path d="M6.1 15.5A1.9 1.9 0 0 1 4.2 13.6" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function BitableIcon({ active }: { active: boolean }) {
  const stroke = active ? "#2563EB" : "#64748B";
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" fill="none" aria-hidden>
      <rect x="3.6" y="4.2" width="12.8" height="11.6" rx="2" stroke={stroke} strokeWidth="1.5" />
      <path d="M3.9 8.1h12.2M7.8 4.5v11M12.2 4.5v11" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function KnowledgeWorkspacePage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeSection, setActiveSection] = useState<KnowledgeSection>("rag");
  const [files, setFiles] = useState<RagFile[]>([]);
  const [selectedUpload, setSelectedUpload] = useState<File | null>(null);
  const [uploadPreview, setUploadPreview] = useState("");
  const [query, setQuery] = useState("RAG 编辑 资料预览 重新索引");
  const [results, setResults] = useState<RagSearchResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedDetail, setSelectedDetail] = useState<RagFileContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [searching, setSearching] = useState(false);
  const [deletingFileId, setDeletingFileId] = useState<string | null>(null);
  const [confirmDeleteFileId, setConfirmDeleteFileId] = useState<string | null>(null);
  const [editingFileId, setEditingFileId] = useState<string | null>(null);
  const [savingFileId, setSavingFileId] = useState<string | null>(null);
  const [loadingContentFileId, setLoadingContentFileId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<EditDraft>(EMPTY_DRAFT);
  const [notice, setNotice] = useState<string | null>(null);

  const isEditing = Boolean(editingFileId && selectedDetail?.file_id === editingFileId);

  const selectedUploadSupported = useMemo(() => {
    if (!selectedUpload) return false;
    const name = selectedUpload.name.toLowerCase();
    return SUPPORTED_EXTENSIONS.some((ext) => name.endsWith(ext)) || selectedUpload.type.startsWith("text/");
  }, [selectedUpload]);

  async function refreshFiles() {
    setLoading(true);
    try {
      setFiles(await listRagFiles());
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "加载知识库失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    listRagFiles()
      .then((items) => {
        if (!cancelled) setFiles(items);
      })
      .catch((error) => {
        if (!cancelled) setNotice(error instanceof Error ? error.message : "加载知识库失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function openFile(fileId: string, options?: { edit?: boolean }) {
    setLoadingContentFileId(fileId);
    setConfirmDeleteFileId(null);
    setNotice(null);
    if (!options?.edit) {
      setEditingFileId(null);
      setEditDraft(EMPTY_DRAFT);
    }
    try {
      const detail = await getRagFileContent(fileId);
      setSelectedDetail(detail);
      if (options?.edit) {
        setEditingFileId(detail.file_id);
        setEditDraft({
          filename: detail.filename,
          source: detail.source,
          note: noteFromMetadata(detail.metadata),
          content: detail.content,
          originalContent: detail.content,
        });
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "加载正文失败");
    } finally {
      setLoadingContentFileId(null);
    }
  }

  function returnToList() {
    setSelectedDetail(null);
    setEditingFileId(null);
    setConfirmDeleteFileId(null);
    setEditDraft(EMPTY_DRAFT);
  }

  function startEditCurrent() {
    if (!selectedDetail) return;
    setEditingFileId(selectedDetail.file_id);
    setConfirmDeleteFileId(null);
    setNotice(null);
    setEditDraft({
      filename: selectedDetail.filename,
      source: selectedDetail.source,
      note: noteFromMetadata(selectedDetail.metadata),
      content: selectedDetail.content,
      originalContent: selectedDetail.content,
    });
  }

  function cancelEdit() {
    setEditingFileId(null);
    setSavingFileId(null);
    setEditDraft(EMPTY_DRAFT);
  }

  async function handleFileChange(file: File | null) {
    setSelectedUpload(file);
    setNotice(null);
    setUploadPreview("");
    if (!file) return;
    const supported = SUPPORTED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext)) || file.type.startsWith("text/");
    if (!supported) {
      setNotice("当前支持导入 pdf、docx、md、txt、json、csv、log。");
      return;
    }
    if (file.name.toLowerCase().endsWith(".pdf") || file.name.toLowerCase().endsWith(".docx")) {
      setUploadPreview("PDF / DOCX 会在后端解析，导入后可在左侧预览解析后的纯文本。");
      return;
    }
    setUploadPreview(await file.text());
  }

  async function handleIngest() {
    if (!selectedUpload || !selectedUploadSupported) return;
    setSubmitting(true);
    setNotice(null);
    try {
      const ingested = await uploadRagFile(selectedUpload, {
        workspace_id: "Feishu_demo_Eko",
        source: "frontend_upload",
        size: selectedUpload.size,
        type: selectedUpload.type || "text/plain",
        last_modified: selectedUpload.lastModified,
      });
      setNotice(`已导入 ${ingested.filename}，切分为 ${ingested.chunk_count} 个 chunk。`);
      setSelectedUpload(null);
      setUploadPreview("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      await refreshFiles();
      await openFile(ingested.file_id);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "导入失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSearch() {
    const trimmed = query.trim();
    if (!trimmed) return;
    setSearching(true);
    setNotice(null);
    setHasSearched(true);
    try {
      const response = await searchRag(trimmed, 8);
      setResults(response.results);
      setNotice(response.results.length ? `检索完成，命中 ${response.results.length} 条资料。` : "未命中资料，请换一个关键词再试。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "检索失败");
    } finally {
      setSearching(false);
    }
  }

  function clearSearch() {
    setQuery("");
    setResults([]);
    setHasSearched(false);
    setNotice(null);
  }

  async function handleDelete(file: RagFile | RagFileContent) {
    if (confirmDeleteFileId !== file.file_id) {
      setConfirmDeleteFileId(file.file_id);
      setNotice(`再次点击确认删除：${file.filename}`);
      return;
    }
    setDeletingFileId(file.file_id);
    setNotice(null);
    try {
      await deleteRagFile(file.file_id);
      setFiles((current) => current.filter((item) => item.file_id !== file.file_id));
      setResults((current) => current.filter((item) => item.source_id !== file.file_id));
      if (selectedDetail?.file_id === file.file_id) {
        returnToList();
      }
      setNotice(`已删除 ${file.filename}。`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "删除失败");
    } finally {
      setDeletingFileId(null);
      setConfirmDeleteFileId(null);
    }
  }

  async function handleSaveEdit() {
    if (!selectedDetail) return;
    const filename = editDraft.filename.trim();
    const source = editDraft.source.trim();
    const content = editDraft.content;
    const trimmedContent = content.trim();
    const contentChanged = content !== editDraft.originalContent;
    if (!filename) {
      setNotice("资料名称不能为空。");
      return;
    }
    if (!source) {
      setNotice("资料来源不能为空。");
      return;
    }
    if (contentChanged && !trimmedContent) {
      setNotice("正文内容不能为空。");
      return;
    }
    setSavingFileId(selectedDetail.file_id);
    setNotice(null);
    try {
      const updated = await updateRagFile(selectedDetail.file_id, {
        filename,
        source,
        metadata: { ...selectedDetail.metadata, note: editDraft.note.trim() },
        ...(contentChanged ? { content } : {}),
      });
      const nextDetail: RagFileContent = {
        ...updated,
        content,
      };
      setSelectedDetail(nextDetail);
      setFiles((current) => current.map((item) => (item.file_id === updated.file_id ? updated : item)));
      setResults((current) =>
        current.map((item) =>
          item.source_id === updated.file_id
            ? {
                ...item,
                title: updated.filename,
                metadata: { ...item.metadata, source: updated.source, ...updated.metadata },
              }
            : item,
        ),
      );
      setEditingFileId(null);
      setEditDraft(EMPTY_DRAFT);
      setNotice(contentChanged ? `已保存并重新索引 ${updated.filename}，当前 ${updated.chunk_count} chunks。` : "已保存资料信息。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSavingFileId(null);
    }
  }

  return (
    <main className="h-full min-h-0 overflow-hidden bg-[#F8F9FA] text-slate-950">
      <div className="grid h-full min-h-0 w-full gap-4 overflow-hidden px-0 py-4 pr-4 lg:grid-cols-[148px_minmax(0,1fr)]">
        <aside className="min-h-0 overflow-y-auto border-r border-slate-200/90 bg-[#F8F9FA] px-3 py-0">
          <nav className="space-y-1" aria-label="知识管理二级导航">
            {[
              { key: "rag" as const, label: "知识库" },
              { key: "bitable" as const, label: "Bitable" },
            ].map((item) => {
              const active = activeSection === item.key;
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setActiveSection(item.key)}
                  className={[
                    "flex w-full items-center gap-2.5 rounded-r-[14px] rounded-l-none px-2.5 py-2.5 text-left text-[13px] font-medium leading-snug transition-colors",
                    active
                      ? "bg-blue-50 text-blue-600 shadow-[inset_4px_0_0_0_#2563EB]"
                      : "text-slate-600 hover:bg-white/90 hover:text-slate-900",
                  ].join(" ")}
                >
                  <span className="flex h-5 w-5 items-center justify-center">
                    {item.key === "rag" ? <KnowledgeIcon active={active} /> : <BitableIcon active={active} />}
                  </span>
                  <span className="min-w-0 flex-1">{item.label}</span>
                </button>
              );
            })}
          </nav>
        </aside>

        {activeSection === "bitable" ? (
          <section className="min-h-0 min-w-0 overflow-y-auto pr-1">
            <div className="pb-4">
              <BitableSourcesPanel />
            </div>
          </section>
        ) : (
          <section className="grid min-h-0 min-w-0 gap-4 overflow-hidden xl:grid-cols-[minmax(0,1fr)_320px]">
            <RagMainWorkspace
              detail={selectedDetail}
              editDraft={editDraft}
              isEditing={isEditing}
              loadingContentFileId={loadingContentFileId}
              notice={notice}
              selectedUpload={selectedUpload}
              uploadPreview={uploadPreview}
              confirmDeleteFileId={confirmDeleteFileId}
              deletingFileId={deletingFileId}
              savingFileId={savingFileId}
              onDraftChange={setEditDraft}
              onCancelEdit={cancelEdit}
              onDelete={handleDelete}
              onSaveEdit={() => void handleSaveEdit()}
            />
            <RagRightRail
              confirmDeleteFileId={confirmDeleteFileId}
              deletingFileId={deletingFileId}
              detail={selectedDetail}
              fileInputRef={fileInputRef}
              files={files}
              hasSearched={hasSearched}
              loading={loading}
              loadingContentFileId={loadingContentFileId}
              notice={notice}
              query={query}
              results={results}
              searching={searching}
              selectedUpload={selectedUpload}
              selectedUploadSupported={selectedUploadSupported}
              submitting={submitting}
              uploadPreview={uploadPreview}
              onClearSearch={clearSearch}
              onDelete={handleDelete}
              onFileChange={handleFileChange}
              onIngest={handleIngest}
              onOpenFile={(fileId, options) => void openFile(fileId, options)}
              onQueryChange={setQuery}
              onSearch={() => void handleSearch()}
            />
          </section>
        )}
      </div>
    </main>
  );
}

function RagMainWorkspace({
  detail,
  editDraft,
  isEditing,
  loadingContentFileId,
  notice,
  selectedUpload,
  uploadPreview,
  confirmDeleteFileId,
  deletingFileId,
  savingFileId,
  onDraftChange,
  onCancelEdit,
  onDelete,
  onSaveEdit,
}: {
  detail: RagFileContent | null;
  editDraft: EditDraft;
  isEditing: boolean;
  loadingContentFileId: string | null;
  notice: string | null;
  selectedUpload: File | null;
  uploadPreview: string;
  confirmDeleteFileId: string | null;
  deletingFileId: string | null;
  savingFileId: string | null;
  onDraftChange: React.Dispatch<React.SetStateAction<EditDraft>>;
  onCancelEdit: () => void;
  onDelete: (file: RagFileContent) => void;
  onSaveEdit: () => void;
}) {
  if (!detail && selectedUpload) {
    return (
      <article className="flex min-h-0 flex-col overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
        <div className="shrink-0 border-b border-slate-100 px-6 py-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h2 className="truncate text-[24px] font-semibold tracking-[-0.05em] text-slate-950">{selectedUpload.name}</h2>
              <p className="mt-2 text-[13px] text-slate-500">待导入文件 · {formatBytes(selectedUpload.size)}</p>
            </div>
            <MainActionBar disabled />
          </div>
        </div>
        <div className="flex min-h-0 flex-1 flex-col gap-5 p-6">
          <div className="grid shrink-0 gap-3 sm:grid-cols-3">
            <InfoCard label="状态" value="待导入" />
            <InfoCard label="文件类型" value={selectedUpload.type || "未知类型"} />
            <InfoCard label="文件大小" value={formatBytes(selectedUpload.size)} />
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto whitespace-pre-wrap rounded-[18px] border border-slate-200 bg-slate-50/80 px-5 py-5 text-[14px] leading-7 text-slate-700">
            {uploadPreview || "该文件会在导入时由后端解析，导入成功后将在这里展示解析后的纯文本。"}
          </div>
        </div>
        {notice ? <p className="shrink-0 border-t border-slate-100 px-6 py-4 text-[13px] text-slate-600">{notice}</p> : null}
      </article>
    );
  }

  if (!detail) {
    return (
      <article className="flex min-h-0 flex-col overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
        <div className="shrink-0 border-b border-slate-100 px-6 py-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-[20px] font-semibold tracking-[-0.04em] text-slate-950">资料预览</h2>
              <p className="mt-1 text-[13px] text-slate-500">当前没有选中的文件</p>
            </div>
            <MainActionBar disabled />
          </div>
        </div>
        <div className="min-h-0 flex-1 p-6">
          <div className="flex h-full min-h-[360px] items-center justify-center rounded-[16px] border border-dashed border-slate-200 bg-slate-50/80 px-6 text-center">
            <div>
              <p className="text-[15px] font-semibold text-slate-800">请选择右侧已入库文件进行预览</p>
              <p className="mt-2 max-w-[360px] text-[13px] leading-6 text-slate-500">导入或点击已有资料后，这里会展示标题、来源、备注和解析后的正文内容。</p>
            </div>
          </div>
        </div>
        {notice ? <p className="shrink-0 border-t border-slate-100 px-6 py-4 text-[13px] text-slate-600">{notice}</p> : null}
      </article>
    );
  }

  return (
    <article className="flex min-h-0 flex-col overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
      <div className="flex shrink-0 flex-col gap-4 border-b border-slate-100 px-6 py-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 className="truncate text-[26px] font-semibold tracking-[-0.05em] text-slate-950">{isEditing ? editDraft.filename || "未命名资料" : detail.filename}</h2>
          <p className="mt-2 truncate text-[13px] text-slate-500">{detail.chunk_count} chunks · {isEditing ? editDraft.source : detail.source}</p>
        </div>
        <MainActionBar
          confirmDeleteActive={confirmDeleteFileId === detail.file_id}
          deleting={deletingFileId === detail.file_id}
          editing={isEditing}
          saving={savingFileId === detail.file_id}
          onCancel={onCancelEdit}
          onDelete={() => onDelete(detail)}
          onSave={onSaveEdit}
        />
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-5 p-6">
        {isEditing ? (
          <div className="grid shrink-0 gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1.4fr)]">
            <EditField label="资料名称" value={editDraft.filename} onChange={(value) => onDraftChange((draft) => ({ ...draft, filename: value }))} />
            <EditField label="来源标识" value={editDraft.source} onChange={(value) => onDraftChange((draft) => ({ ...draft, source: value }))} />
            <EditField label="备注" value={editDraft.note} onChange={(value) => onDraftChange((draft) => ({ ...draft, note: value }))} />
          </div>
        ) : (
          <div className="grid shrink-0 gap-3 sm:grid-cols-3">
            <InfoCard label="来源" value={detail.source} />
            <InfoCard label="创建时间" value={formatDate(detail.created_at)} />
            <InfoCard label="备注" value={noteFromMetadata(detail.metadata) || "暂无备注"} />
          </div>
        )}

        {isEditing ? (
          <label className="flex min-h-0 flex-1 flex-col">
            <span className="mb-2 block text-[13px] font-semibold text-slate-700">正文内容</span>
            <textarea
              value={editDraft.content}
              onChange={(event) => onDraftChange((draft) => ({ ...draft, content: event.target.value }))}
              disabled={loadingContentFileId === detail.file_id}
              className="min-h-0 flex-1 resize-none rounded-[18px] border border-slate-200 bg-slate-50/80 px-4 py-4 font-mono text-[13px] leading-6 text-slate-800 outline-none transition focus:border-blue-400 focus:bg-white disabled:bg-slate-100 disabled:text-slate-400"
              placeholder={loadingContentFileId === detail.file_id ? "正在加载正文..." : "编辑正文后保存，会重新切分并写入向量库"}
            />
          </label>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto whitespace-pre-wrap rounded-[18px] border border-slate-200 bg-slate-50/80 px-5 py-5 text-[14px] leading-7 text-slate-700">
            {loadingContentFileId === detail.file_id ? "正在加载正文..." : detail.content || "这份资料暂无可预览正文。"}
          </div>
        )}
      </div>
    </article>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-[16px] border border-slate-200 bg-white px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{label}</p>
      <p className="mt-1 truncate text-[13px] font-medium text-slate-700">{value}</p>
    </div>
  );
}

function EditField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block min-w-0 rounded-[16px] border border-slate-200 bg-white px-4 py-3">
      <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-7 w-full bg-transparent text-[13px] font-medium text-slate-800 outline-none placeholder:text-slate-400"
        placeholder={`请输入${label}`}
      />
    </label>
  );
}

function MainActionBar({
  confirmDeleteActive = false,
  deleting = false,
  disabled = false,
  editing = false,
  saving = false,
  onCancel,
  onDelete,
  onSave,
}: {
  confirmDeleteActive?: boolean;
  deleting?: boolean;
  disabled?: boolean;
  editing?: boolean;
  saving?: boolean;
  onCancel?: () => void;
  onDelete?: () => void;
  onSave?: () => void;
}) {
  const inactive = disabled || !editing;
  return (
    <div className="flex shrink-0 flex-wrap gap-2">
      <button
        type="button"
        onClick={onSave}
        disabled={inactive || saving}
        className="h-9 rounded-[11px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-45"
      >
        {saving ? "保存中" : "保存编辑"}
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={inactive || saving}
        className="h-9 rounded-[11px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-45"
      >
        取消编辑
      </button>
      <button
        type="button"
        onClick={onDelete}
        disabled={disabled || deleting}
        className={[
          "h-9 rounded-[11px] px-3 text-[12px] font-semibold transition disabled:cursor-not-allowed disabled:opacity-45",
          confirmDeleteActive ? "bg-rose-600 text-white hover:bg-rose-700" : "bg-rose-50 text-rose-600 hover:bg-rose-100",
        ].join(" ")}
      >
        {deleting ? "删除中" : confirmDeleteActive ? "确认删除" : "删除文件"}
      </button>
    </div>
  );
}

function RagRightRail({
  confirmDeleteFileId,
  deletingFileId,
  detail,
  fileInputRef,
  files,
  hasSearched,
  loading,
  loadingContentFileId,
  notice,
  query,
  results,
  searching,
  selectedUpload,
  selectedUploadSupported,
  submitting,
  uploadPreview,
  onClearSearch,
  onDelete,
  onFileChange,
  onIngest,
  onOpenFile,
  onQueryChange,
  onSearch,
}: {
  confirmDeleteFileId: string | null;
  deletingFileId: string | null;
  detail: RagFileContent | null;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  files: RagFile[];
  hasSearched: boolean;
  loading: boolean;
  loadingContentFileId: string | null;
  notice: string | null;
  query: string;
  results: RagSearchResult[];
  searching: boolean;
  selectedUpload: File | null;
  selectedUploadSupported: boolean;
  submitting: boolean;
  uploadPreview: string;
  onClearSearch: () => void;
  onDelete: (file: RagFile | RagFileContent) => void;
  onFileChange: (file: File | null) => Promise<void>;
  onIngest: () => void;
  onOpenFile: (fileId: string, options?: { edit?: boolean }) => void;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
}) {
  return (
    <aside className="min-h-0 min-w-0 space-y-4 overflow-y-auto pr-1">
      <UploadPanel
        fileInputRef={fileInputRef}
        selectedUpload={selectedUpload}
        selectedUploadSupported={selectedUploadSupported}
        submitting={submitting}
        uploadPreview={uploadPreview}
        onFileChange={onFileChange}
        onIngest={onIngest}
      />
      <section className="rounded-[22px] border border-slate-200 bg-white p-4 shadow-[0_18px_48px_rgba(15,23,42,0.05)]">
        <LibrarySearchBox
          hasSearched={hasSearched}
          query={query}
          searching={searching}
          onClearSearch={onClearSearch}
          onQueryChange={onQueryChange}
          onSearch={onSearch}
        />
        {hasSearched ? (
          <SearchResultsList
            loadingContentFileId={loadingContentFileId}
            results={results}
            searching={searching}
            onOpenFile={onOpenFile}
          />
        ) : (
          <FileList
            confirmDeleteFileId={confirmDeleteFileId}
            deletingFileId={deletingFileId}
            files={files}
            loading={loading}
            loadingContentFileId={loadingContentFileId}
            selectedFileId={detail?.file_id ?? null}
            onDelete={onDelete}
            onOpenFile={onOpenFile}
          />
        )}
      </section>

      {notice ? <p className="rounded-[16px] border border-slate-200 bg-white px-4 py-3 text-[13px] leading-6 text-slate-600">{notice}</p> : null}
    </aside>
  );
}

function UploadPanel({
  fileInputRef,
  selectedUpload,
  selectedUploadSupported,
  submitting,
  uploadPreview,
  onFileChange,
  onIngest,
}: {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  selectedUpload: File | null;
  selectedUploadSupported: boolean;
  submitting: boolean;
  uploadPreview: string;
  onFileChange: (file: File | null) => Promise<void>;
  onIngest: () => void;
}) {
  return (
    <section className="rounded-[22px] border border-slate-200 bg-white p-4 shadow-[0_18px_48px_rgba(15,23,42,0.05)]">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[15px] font-semibold text-slate-950">本地导入</h2>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="h-9 rounded-[11px] bg-slate-950 px-3 text-[12px] font-semibold text-white transition hover:bg-slate-800"
        >
          选择文件
        </button>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.md,.txt,.json,.csv,.log,text/*,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="sr-only"
        onChange={(event) => void onFileChange(event.target.files?.[0] ?? null)}
      />
      {selectedUpload ? (
        <div className="mt-3 rounded-[16px] border border-slate-200 bg-slate-50 p-3">
          <p className="truncate text-[13px] font-semibold text-slate-900">{selectedUpload.name}</p>
          <p className="mt-1 text-[12px] text-slate-500">{formatBytes(selectedUpload.size)}</p>
          <p className="mt-3 text-[12px] leading-5 text-slate-500">{uploadPreview ? "已读取本地文件，点击导入后会在中间栏预览入库正文。" : "文件会上传到后端解析，导入成功后在中间栏预览。"}</p>
          <button
            type="button"
            onClick={onIngest}
            disabled={submitting || !selectedUploadSupported}
            className="mt-3 h-9 w-full rounded-[11px] bg-blue-600 text-[12px] font-semibold text-white transition hover:bg-blue-700 disabled:bg-slate-300"
          >
            {submitting ? "导入中..." : "导入知识库"}
          </button>
        </div>
      ) : (
        <p className="mt-3 rounded-[16px] border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-[12px] leading-5 text-slate-500">
          支持 pdf、docx、md、txt、json、csv、log。导入后可在左侧预览和编辑。
        </p>
      )}
    </section>
  );
}

function LibrarySearchBox({
  hasSearched,
  query,
  searching,
  onClearSearch,
  onQueryChange,
  onSearch,
}: {
  hasSearched: boolean;
  query: string;
  searching: boolean;
  onClearSearch: () => void;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
}) {
  return (
    <div className="mb-4 border-b border-slate-100 pb-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[15px] font-semibold text-slate-950">已入库文件</h2>
        {hasSearched ? (
          <button type="button" onClick={onClearSearch} className="text-[12px] font-semibold text-slate-400 transition hover:text-slate-700">
            清空
          </button>
        ) : null}
      </div>
      <div className="mt-3 flex gap-2">
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") onSearch();
          }}
          className="h-10 min-w-0 flex-1 rounded-[12px] border border-slate-200 px-3 text-[13px] text-slate-800 outline-none focus:border-blue-400"
          placeholder="搜索资料关键词"
        />
        <button
          type="button"
          onClick={onSearch}
          disabled={searching || !query.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] bg-blue-600 text-white transition hover:bg-blue-700 disabled:bg-slate-300"
          aria-label="搜索"
          title="搜索"
        >
          {searching ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/50 border-t-white" />
          ) : (
            <SearchIcon />
          )}
        </button>
      </div>
    </div>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-4.5 w-4.5" fill="none" aria-hidden>
      <circle cx="8.8" cy="8.8" r="5.2" stroke="currentColor" strokeWidth="1.8" />
      <path d="m12.7 12.7 3.1 3.1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function SearchResultsList({
  loadingContentFileId,
  results,
  searching,
  onOpenFile,
}: {
  loadingContentFileId: string | null;
  results: RagSearchResult[];
  searching: boolean;
  onOpenFile: (fileId: string, options?: { edit?: boolean }) => void;
}) {
  return (
    <div>
      <h2 className="text-[15px] font-semibold text-slate-950">搜索结果</h2>
      <div className="mt-3 space-y-2">
        {searching ? <p className="text-[13px] text-slate-500">检索中...</p> : null}
        {!searching && results.length === 0 ? (
          <p className="rounded-[16px] border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-[12px] leading-5 text-slate-500">
            暂无检索结果。可以试试“RAG 编辑”“资料预览”“重新索引”等关键词。
          </p>
        ) : null}
        {results.map((result) => (
          <button
            key={result.chunk_id}
            type="button"
            onClick={() => onOpenFile(result.source_id)}
            className="w-full rounded-[16px] border border-slate-200 bg-white p-3 text-left transition hover:border-blue-200 hover:bg-blue-50/40"
          >
            <div className="flex items-center justify-between gap-3">
              <p className="min-w-0 truncate text-[13px] font-semibold text-slate-900">{result.title}</p>
              <span className="shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700">{(result.score * 100).toFixed(0)}%</span>
            </div>
            <p className="mt-2 line-clamp-3 text-[12px] leading-5 text-slate-500">{shortText(result.content, 220)}</p>
            {loadingContentFileId === result.source_id ? <p className="mt-2 text-[11px] font-semibold text-blue-500">加载正文中...</p> : null}
          </button>
        ))}
      </div>
    </div>
  );
}

function FileList({
  confirmDeleteFileId,
  deletingFileId,
  files,
  loading,
  loadingContentFileId,
  selectedFileId,
  onDelete,
  onOpenFile,
}: {
  confirmDeleteFileId: string | null;
  deletingFileId: string | null;
  files: RagFile[];
  loading: boolean;
  loadingContentFileId: string | null;
  selectedFileId: string | null;
  onDelete: (file: RagFile) => void;
  onOpenFile: (fileId: string, options?: { edit?: boolean }) => void;
}) {
  return (
    <div>
      <div className="space-y-2">
        {loading ? <p className="text-[13px] text-slate-500">加载中...</p> : null}
        {!loading && files.length === 0 ? <p className="text-[13px] text-slate-500">还没有 RAG 文件。</p> : null}
        {files.map((file) => {
          const selected = selectedFileId === file.file_id;
          return (
            <div
              key={file.file_id}
              className={[
                "rounded-[16px] border p-3 transition",
                selected ? "border-blue-200 bg-blue-50/50" : "border-slate-200 bg-white hover:border-slate-300",
              ].join(" ")}
            >
              <button type="button" onClick={() => onOpenFile(file.file_id)} className="block w-full text-left">
                <p className="truncate text-[13px] font-semibold text-slate-900">{file.filename}</p>
                <p className="mt-1 truncate text-[12px] text-slate-500">{file.chunk_count} chunks · {file.source}</p>
                {noteFromMetadata(file.metadata) ? <p className="mt-1 line-clamp-2 text-[12px] text-slate-500">{noteFromMetadata(file.metadata)}</p> : null}
                {loadingContentFileId === file.file_id ? <p className="mt-2 text-[11px] font-semibold text-blue-500">加载正文中...</p> : null}
              </button>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => onOpenFile(file.file_id, { edit: true })}
                  className="h-8 flex-1 rounded-[10px] bg-slate-100 text-[12px] font-semibold text-slate-700 transition hover:bg-slate-200"
                >
                  编辑
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(file)}
                  disabled={deletingFileId === file.file_id}
                  className={[
                    "h-8 flex-1 rounded-[10px] text-[12px] font-semibold transition disabled:bg-slate-100 disabled:text-slate-400",
                    confirmDeleteFileId === file.file_id ? "bg-rose-600 text-white hover:bg-rose-700" : "bg-rose-50 text-rose-600 hover:bg-rose-100",
                  ].join(" ")}
                >
                  {deletingFileId === file.file_id ? "删除中" : confirmDeleteFileId === file.file_id ? "确认删除" : "删除"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
