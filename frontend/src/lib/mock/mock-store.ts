import { MOCK_SYNC_SESSIONS } from "@/lib/mock/sync-sessions-data";
import type { SyncSession } from "@/lib/sync/live-session-list-data";
import type { RagFile, RagSearchResponse, RagSearchResult } from "@/lib/rag-api";

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

type MockState = {
  sessions: SyncSession[];
  ragFiles: RagFile[];
};

declare global {
  // eslint-disable-next-line no-var
  var __EKO_MOCK_STATE__: MockState | undefined;
}

function nowIso() {
  return new Date().toISOString();
}

function ensureState(): MockState {
  if (!globalThis.__EKO_MOCK_STATE__) {
    globalThis.__EKO_MOCK_STATE__ = {
      sessions: deepClone(MOCK_SYNC_SESSIONS),
      ragFiles: [
        {
          file_id: "rag-demo-template-1",
          filename: "运营方案模板（示例）.md",
          source: "seed",
          chunk_count: 18,
          metadata: { workspace_id: "Feishu_demo_Eko", seeded: true },
          created_at: nowIso(),
        },
        {
          file_id: "rag-demo-handbook-1",
          filename: "活动运营手册 v2.1（示例）.pdf",
          source: "seed",
          chunk_count: 42,
          metadata: { workspace_id: "Feishu_demo_Eko", seeded: true },
          created_at: nowIso(),
        },
      ],
    };
  }
  return globalThis.__EKO_MOCK_STATE__;
}

export function listMockSessions(): SyncSession[] {
  return ensureState().sessions;
}

export function getMockSession(sessionId: string): SyncSession | null {
  const state = ensureState();
  return state.sessions.find((s) => s.session_id === sessionId) ?? null;
}

export function updateMockSession(sessionId: string, patch: Partial<SyncSession>): SyncSession | null {
  const state = ensureState();
  const index = state.sessions.findIndex((s) => s.session_id === sessionId);
  if (index < 0) return null;
  const next = { ...state.sessions[index], ...patch };
  state.sessions[index] = next;
  return next;
}

export function archiveMockSession(sessionId: string): { session: SyncSession | null; createdRagFile?: RagFile } {
  const current = getMockSession(sessionId);
  if (!current) return { session: null };

  const updatedAt = nowIso();
  const artifact = {
    ...(current.artifact ?? {}),
    status: "completed",
    progress: 1,
    current_step: "已确认保存（mock）",
  };

  const session = updateMockSession(sessionId, {
    status: "已同步",
    updated_at: updatedAt,
    artifact,
  });

  // Simulate “回流知识库”：给知识库新增一条与会话关联的文件
  const state = ensureState();
  const fileId = `rag-from-session-${encodeURIComponent(sessionId)}-${Date.now()}`;
  const createdRagFile: RagFile = {
    file_id: fileId,
    filename: `${current.title || sessionId}（归档回流）.md`,
    source: "session_archive",
    chunk_count: 12,
    metadata: {
      workspace_id: "Feishu_demo_Eko",
      session_id: sessionId,
      archived_at: updatedAt,
    },
    created_at: updatedAt,
  };
  state.ragFiles = [createdRagFile, ...state.ragFiles];

  return { session, createdRagFile };
}

export function listMockRagFiles(): RagFile[] {
  return ensureState().ragFiles;
}

export function deleteMockRagFile(fileId: string): boolean {
  const state = ensureState();
  const before = state.ragFiles.length;
  state.ragFiles = state.ragFiles.filter((f) => f.file_id !== fileId);
  return state.ragFiles.length !== before;
}

export function searchMockRag(query: string, limit: number): RagSearchResponse {
  const trimmed = query.trim().toLowerCase();
  const files = ensureState().ragFiles;
  const hits = trimmed
    ? files.filter((f) => f.filename.toLowerCase().includes(trimmed) || JSON.stringify(f.metadata ?? {}).toLowerCase().includes(trimmed))
    : files;

  const results: RagSearchResult[] = hits.slice(0, limit).map((file, index) => ({
    chunk_id: `${file.file_id}:chunk:${index + 1}`,
    source_id: file.file_id,
    source_type: "rag_file",
    title: file.filename,
    content: `（mock）命中来源：${file.filename}`,
    score: 0.72 - index * 0.03,
    metadata: file.metadata ?? {},
  }));

  return { query, results };
}

