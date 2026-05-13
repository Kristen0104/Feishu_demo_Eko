"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { deleteRagFile, listRagFiles, searchRag, uploadRagFile, type RagFile, type RagSearchResult } from "@/lib/rag-api";
import { BitableSourcesPanel } from "@/components/knowledge/BitableSourcesPanel";

const SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".md", ".txt", ".json", ".csv", ".log"];

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function shortText(text: string, max = 180) {
  const normalized = text.replace(/\s+/g, " ").trim();
  return normalized.length > max ? `${normalized.slice(0, max)}...` : normalized;
}

export function KnowledgeWorkspacePage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<RagFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [query, setQuery] = useState("RAG 知识库资料 飞书文档 API 活动方案");
  const [results, setResults] = useState<RagSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [searching, setSearching] = useState(false);
  const [deletingFileId, setDeletingFileId] = useState<string | null>(null);
  const [confirmDeleteFileId, setConfirmDeleteFileId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedFileSupported = useMemo(() => {
    if (!selectedFile) return false;
    const name = selectedFile.name.toLowerCase();
    return SUPPORTED_EXTENSIONS.some((ext) => name.endsWith(ext)) || selectedFile.type.startsWith("text/");
  }, [selectedFile]);

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

  async function handleFileChange(file: File | null) {
    setSelectedFile(file);
    setNotice(null);
    setPreview("");
    if (!file) return;
    const supported = SUPPORTED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext)) || file.type.startsWith("text/");
    if (!supported) {
      setNotice("当前支持导入 pdf、docx、md、txt、json、csv、log。");
      return;
    }
    if (file.name.toLowerCase().endsWith(".pdf") || file.name.toLowerCase().endsWith(".docx")) {
      setPreview("PDF / DOCX 会在后端解析，导入后可用检索框验证内容。");
      return;
    }
    setPreview(await file.text());
  }

  async function handleIngest() {
    if (!selectedFile || !selectedFileSupported) return;
    setSubmitting(true);
    setNotice(null);
    try {
      const ingested = await uploadRagFile(
        selectedFile,
        {
          workspace_id: "Feishu_demo_Eko",
          source: "frontend_upload",
          size: selectedFile.size,
          type: selectedFile.type || "text/plain",
          last_modified: selectedFile.lastModified,
        },
      );
      setNotice(`已导入 ${ingested.filename}，切分为 ${ingested.chunk_count} 个 chunk。`);
      setSelectedFile(null);
      setPreview("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      await refreshFiles();
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
    try {
      const response = await searchRag(trimmed, 5);
      setResults(response.results);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "检索失败");
    } finally {
      setSearching(false);
    }
  }

  async function handleDelete(file: RagFile) {
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
      setNotice(`已删除 ${file.filename}。`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "删除失败");
    } finally {
      setDeletingFileId(null);
      setConfirmDeleteFileId(null);
    }
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-[#F8F9FA] px-3 py-4 sm:px-5 lg:px-6 lg:py-6">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-5">
        <BitableSourcesPanel />

        <section className="rounded-[16px] border border-slate-200 bg-white p-3 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <h1 className="text-[22px] font-semibold text-slate-950">知识库导入</h1>
              <p className="mt-2 max-w-[720px] text-[14px] leading-6 text-slate-500">
                导入后的文本会进入 RAG 向量库，Agent 每轮会通过检索结果注入上下文。
              </p>
            </div>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex h-10 w-full shrink-0 items-center justify-center rounded-[12px] bg-blue-600 px-4 text-[13px] font-semibold text-white shadow-sm transition hover:bg-blue-700 sm:w-auto"
            >
              选择文件
            </button>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.md,.txt,.json,.csv,.log,text/*,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="sr-only"
            onChange={(event) => void handleFileChange(event.target.files?.[0] ?? null)}
          />

          <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div className="min-h-[220px] rounded-[14px] border border-dashed border-slate-300 bg-slate-50/80 p-4">
              {selectedFile ? (
                <div className="flex h-full flex-col">
                  <div className="flex min-w-0 items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-[14px] font-semibold text-slate-900">{selectedFile.name}</p>
                      <p className="mt-1 text-[12px] text-slate-500">{formatBytes(selectedFile.size)}</p>
                    </div>
                    <button
                      type="button"
                      onClick={handleIngest}
                      disabled={submitting || !selectedFileSupported}
                      className="inline-flex h-9 shrink-0 items-center justify-center rounded-[11px] bg-slate-950 px-3 text-[12px] font-semibold text-white disabled:bg-slate-300"
                    >
                      {submitting ? "导入中..." : "导入 RAG"}
                    </button>
                  </div>
                  <pre className="mt-4 min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded-[12px] border border-slate-200 bg-white p-3 text-[12px] leading-5 text-slate-600">
                    {preview ? shortText(preview, 1800) : "文件会上传到后端解析。"}
                  </pre>
                </div>
              ) : (
                <div className="flex h-full min-h-[188px] flex-col items-center justify-center text-center">
                  <p className="text-[15px] font-semibold text-slate-800">选择本地文本文件导入 RAG</p>
                  <p className="mt-2 max-w-[420px] text-[13px] leading-6 text-slate-500">支持 pdf、docx、md、txt、json、csv、log。PDF / DOCX 会在后端解析后入库。</p>
                </div>
              )}
            </div>

            <div className="rounded-[14px] border border-slate-200 bg-white p-4">
              <h2 className="text-[14px] font-semibold text-slate-950">已入库文件</h2>
              <div className="mt-3 max-h-[264px] space-y-2 overflow-y-auto pr-1">
                {loading ? <p className="text-[13px] text-slate-500">加载中...</p> : null}
                {!loading && files.length === 0 ? <p className="text-[13px] text-slate-500">还没有 RAG 文件。</p> : null}
                {files.map((file) => (
                  <div key={file.file_id} className="rounded-[12px] border border-slate-200 px-3 py-2.5">
                    <div className="flex min-w-0 items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-semibold text-slate-900">{file.filename}</p>
                        <p className="mt-1 text-[12px] text-slate-500">{file.chunk_count} chunks</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleDelete(file)}
                        disabled={deletingFileId === file.file_id}
                        className={[
                          "shrink-0 rounded-[9px] px-2.5 py-1 text-[11px] font-semibold transition disabled:bg-slate-100 disabled:text-slate-400",
                          confirmDeleteFileId === file.file_id
                            ? "bg-rose-600 text-white hover:bg-rose-700"
                            : "bg-rose-50 text-rose-600 hover:bg-rose-100",
                        ].join(" ")}
                      >
                        {deletingFileId === file.file_id ? "删除中" : confirmDeleteFileId === file.file_id ? "确认删除" : "删除"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {notice ? <p className="mt-4 text-[13px] text-slate-600">{notice}</p> : null}
        </section>

        <section className="rounded-[16px] border border-slate-200 bg-white p-3 shadow-[0_12px_30px_rgba(15,23,42,0.04)] sm:p-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="h-10 min-w-0 flex-1 rounded-[12px] border border-slate-200 px-3 text-[14px] text-slate-800 outline-none focus:border-blue-400"
              placeholder="输入检索问题"
            />
            <button
              type="button"
              onClick={() => void handleSearch()}
              disabled={searching || !query.trim()}
              className="inline-flex h-10 w-full shrink-0 items-center justify-center rounded-[12px] bg-blue-600 px-4 text-[13px] font-semibold text-white disabled:bg-slate-300 sm:w-auto"
            >
              {searching ? "检索中..." : "测试检索"}
            </button>
          </div>
          <div className="mt-4 space-y-3">
            {results.map((result) => (
              <article key={result.chunk_id} className="rounded-[14px] border border-slate-200 p-4">
                <div className="flex min-w-0 items-center justify-between gap-3">
                  <h3 className="truncate text-[14px] font-semibold text-slate-950">{result.title}</h3>
                  <span className="shrink-0 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-700">{(result.score * 100).toFixed(0)}%</span>
                </div>
                <p className="mt-2 text-[13px] leading-6 text-slate-600">{shortText(result.content, 260)}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
