import { readAccessToken } from "@/lib/auth-token";
import { apiUrl, fetchEkoJson, type EkoApiEnvelope } from "@/lib/eko-api";

export type RagFile = {
  file_id: string;
  filename: string;
  source: string;
  chunk_count: number;
  metadata: Record<string, unknown>;
  created_at?: string | null;
};

export type RagSearchResult = {
  chunk_id: string;
  source_id: string;
  source_type: string;
  title: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
};

export type RagSearchResponse = {
  query: string;
  results: RagSearchResult[];
};

export type RagFileContent = RagFile & {
  content: string;
};

export type RagFileUpdatePayload = {
  filename?: string;
  source?: string;
  metadata?: Record<string, unknown>;
  content?: string;
};

export function listRagFiles(): Promise<RagFile[]> {
  return fetchEkoJson<RagFile[]>("/api/v1/rag/files", { cache: "no-store" });
}

export function ingestRagFile(payload: {
  filename: string;
  source: string;
  content: string;
  metadata?: Record<string, unknown>;
}): Promise<RagFile> {
  return fetchEkoJson<RagFile>("/api/v1/rag/files", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      metadata: payload.metadata ?? {},
    }),
  });
}

export async function uploadRagFile(file: File, metadata?: Record<string, unknown>): Promise<RagFile> {
  const form = new FormData();
  form.set("file", file);
  if (metadata) form.set("metadata", JSON.stringify(metadata));

  const headers = new Headers();
  const token = readAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(apiUrl("/api/v1/rag/files/upload"), {
    method: "POST",
    headers,
    body: form,
  });

  const json = (await res.json().catch(() => null)) as EkoApiEnvelope<RagFile> | { detail?: string; message?: string } | null;
  if (!json || !("code" in json)) {
    const detail = json && "detail" in json && typeof json.detail === "string" ? json.detail : `HTTP ${res.status}`;
    throw new Error(detail);
  }
  if (!res.ok || json.code !== 0) {
    throw new Error(json.message || `HTTP ${res.status}`);
  }
  return json.data;
}

export function deleteRagFile(fileId: string): Promise<boolean> {
  return fetchEkoJson<boolean>(`/api/v1/rag/files/${encodeURIComponent(fileId)}`, {
    method: "DELETE",
  });
}

export function getRagFileContent(fileId: string): Promise<RagFileContent> {
  return fetchEkoJson<RagFileContent>(`/api/v1/rag/files/${encodeURIComponent(fileId)}/content`, {
    cache: "no-store",
  });
}

export function updateRagFile(fileId: string, payload: RagFileUpdatePayload): Promise<RagFile> {
  return fetchEkoJson<RagFile>(`/api/v1/rag/files/${encodeURIComponent(fileId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function searchRag(query: string, limit = 5): Promise<RagSearchResponse> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  return fetchEkoJson<RagSearchResponse>(`/api/v1/rag/search?${params.toString()}`, { cache: "no-store" });
}
