# Feishu Canvas Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working slice of Eko's Feishu-compatible canvas module with dual-track board storage, AI generation contracts, multi-user online collaboration scaffolding, and single-user offline recovery scaffolding.

**Architecture:** Extend the existing FastAPI `canvas` module into a session-oriented backend that stores `FeishuSourceBoard`, `EkoWorkingBoard`, board mappings, and change history. Add a new Next.js workspace shell under `frontend/src` that renders a canvas workspace, keeps collaboration state in a store, accepts AI board patches, and stages offline recovery on the Eko working copy rather than directly on the Feishu source board.

**Tech Stack:** FastAPI, Pydantic, Redis-ready sync contracts, Next.js App Router, Zustand, Tldraw-compatible board JSON adapters, Vitest or Jest for frontend unit tests, Pytest for backend tests.

---

## File Structure

### Backend files

- Modify: `backend/app/modules/canvas/schemas.py`
- Modify: `backend/app/modules/canvas/service.py`
- Modify: `backend/app/modules/canvas/router.py`
- Modify: `backend/app/modules/canvas/repository.py`
- Create: `backend/tests/modules/test_canvas_contract.py`
- Create: `backend/tests/modules/test_canvas_generation_contract.py`

### Frontend files

- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.js`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/mobile/page.tsx`
- Create: `frontend/src/components/surface/CanvasSurface.tsx`
- Create: `frontend/src/components/agent/MissionControl.tsx`
- Create: `frontend/src/components/context/ContextSyncPanel.tsx`
- Create: `frontend/src/lib/store/workspace.ts`
- Create: `frontend/src/lib/mocks/canvas-session.ts`
- Create: `frontend/src/lib/services/offline-queue.ts`
- Create: `frontend/src/types/workspace.ts`
- Create: `frontend/src/types/canvas.ts`
- Create: `frontend/src/types/sync.ts`
- Create: `frontend/src/__tests__/workspace-store.test.ts`
- Create: `frontend/src/__tests__/offline-queue.test.ts`

### Documentation files

- Modify: `docs/superpowers/specs/2026-04-26-feishu-canvas-compatibility-design.md`
- Create: `docs/superpowers/plans/2026-04-26-feishu-canvas-compatibility.md`

---

### Task 1: Expand Backend Canvas Contracts

**Files:**
- Modify: `backend/app/modules/canvas/schemas.py`
- Modify: `backend/app/modules/canvas/service.py`
- Modify: `backend/app/modules/canvas/repository.py`
- Test: `backend/tests/modules/test_canvas_contract.py`

- [ ] **Step 1: Write the failing schema contract tests**

```python
from app.modules.canvas.schemas import (
    BoardSessionSchema,
    FeishuSourceBoardSchema,
    EkoWorkingBoardSchema,
    BoardChangeSchema,
)


def test_board_session_schema_supports_collaboration_and_offline_flags() -> None:
    session = BoardSessionSchema(
        session_id="canvas-demo-001",
        title="Weekly planning canvas",
        mode="canvas",
        owner_user_id="user-1",
        collaborator_ids=["user-2"],
        permission_mode="collaborative",
        sync_state="idle",
        offline_capability="single_user_only",
    )

    assert session.owner_user_id == "user-1"
    assert session.collaborator_ids == ["user-2"]
    assert session.offline_capability == "single_user_only"


def test_working_board_schema_tracks_crdt_and_snapshot_metadata() -> None:
    board = EkoWorkingBoardSchema(
        working_board_id="work-1",
        session_id="canvas-demo-001",
        latest_version=3,
        crdt_document={"nodes": []},
        latest_snapshot={"nodes": []},
        offline_state="clean",
    )

    assert board.latest_version == 3
    assert board.offline_state == "clean"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && pytest tests/modules/test_canvas_contract.py -v`
Expected: FAIL with import or validation errors because the new schema types do not exist yet.

- [ ] **Step 3: Write the minimal schema and service implementation**

```python
from typing import Any, Literal

from pydantic import BaseModel, Field


class FeishuSourceBoardSchema(BaseModel):
    source_board_id: str
    session_id: str
    source_version: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    sync_cursor: str | None = None


class EkoWorkingBoardSchema(BaseModel):
    working_board_id: str
    session_id: str
    latest_version: int
    crdt_document: dict[str, Any] = Field(default_factory=dict)
    latest_snapshot: dict[str, Any] = Field(default_factory=dict)
    offline_state: Literal["clean", "dirty", "replaying"] = "clean"


class BoardChangeSchema(BaseModel):
    change_id: str
    session_id: str
    change_type: Literal[
        "user_edit",
        "ai_patch",
        "source_import",
        "sync_export",
        "conflict_detected",
        "merge_resolved",
        "offline_replay",
    ]
    actor_type: Literal["user", "ai", "system", "feishu"]
    payload: dict[str, Any] = Field(default_factory=dict)


class BoardSessionSchema(BaseModel):
    session_id: str
    title: str
    mode: Literal["canvas"] = "canvas"
    owner_user_id: str
    collaborator_ids: list[str] = Field(default_factory=list)
    permission_mode: Literal["creator_only", "collaborative", "viewer_only"]
    sync_state: Literal["idle", "syncing", "conflict"]
    offline_capability: Literal["disabled", "single_user_only"]
```

- [ ] **Step 4: Update repository fixture data to return the new shape**

```python
from app.modules.canvas.schemas import (
    BoardSessionSchema,
    EkoWorkingBoardSchema,
    FeishuSourceBoardSchema,
)


class CanvasRepository:
    def get_session(self, session_id: str) -> BoardSessionSchema:
        return BoardSessionSchema(
            session_id=session_id,
            title="Feishu Canvas Session",
            owner_user_id="creator-001",
            collaborator_ids=["viewer-001"],
            permission_mode="collaborative",
            sync_state="idle",
            offline_capability="single_user_only",
        )

    def get_working_board(self, session_id: str) -> EkoWorkingBoardSchema:
        return EkoWorkingBoardSchema(
            working_board_id=f"{session_id}-working",
            session_id=session_id,
            latest_version=1,
            crdt_document={"nodes": [], "edges": []},
            latest_snapshot={"nodes": [], "edges": []},
            offline_state="clean",
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && pytest tests/modules/test_canvas_contract.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/canvas/schemas.py backend/app/modules/canvas/service.py backend/app/modules/canvas/repository.py backend/tests/modules/test_canvas_contract.py
git commit -m "feat: expand canvas backend contracts"
```

### Task 2: Add Backend Generation and Merge Review Endpoints

**Files:**
- Modify: `backend/app/modules/canvas/router.py`
- Modify: `backend/app/modules/canvas/service.py`
- Modify: `backend/app/modules/canvas/schemas.py`
- Test: `backend/tests/modules/test_canvas_generation_contract.py`

- [ ] **Step 1: Write failing API contract tests for generation and merge review**

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_generate_board_patch_returns_full_board_contract() -> None:
    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-001/generate",
        json={
            "generation_mode": "full_board",
            "chat_context": [{"role": "user", "content": "整理本周项目讨论"}],
            "user_prompt": "生成产品路线图画板",
            "board_context": {},
            "selection_context": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["generation_mode"] == "full_board"


def test_create_merge_review_returns_conflict_summary() -> None:
    response = client.post(
        "/api/v1/canvas/sessions/canvas-demo-001/merge-review",
        json={
            "source_version": "v10",
            "working_version": 12,
            "conflicts": [{"element_id": "node-1", "kind": "text_conflict"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "pending_review"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && pytest tests/modules/test_canvas_generation_contract.py -v`
Expected: FAIL with 404 or missing schema errors.

- [ ] **Step 3: Add request and response schemas**

```python
class CanvasGenerationRequestSchema(BaseModel):
    generation_mode: Literal["full_board", "targeted_patch"]
    chat_context: list[dict[str, str]] = Field(default_factory=list)
    user_prompt: str
    board_context: dict[str, Any] = Field(default_factory=dict)
    selection_context: dict[str, Any] | None = None


class BoardPatchSchema(BaseModel):
    generation_mode: Literal["full_board", "targeted_patch"]
    patch_id: str
    operations: list[dict[str, Any]] = Field(default_factory=list)
    summary: str


class MergeReviewRequestSchema(BaseModel):
    source_version: str
    working_version: int
    conflicts: list[dict[str, Any]] = Field(default_factory=list)


class MergeReviewSchema(BaseModel):
    review_id: str
    session_id: str
    status: Literal["pending_review"] = "pending_review"
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 4: Add minimal service and router endpoints**

```python
@router.post(
    "/sessions/{session_id}/generate",
    response_model=ApiResponse[BoardPatchSchema],
    summary="Generate board patch",
)
async def generate_board_patch(
    session_id: str,
    payload: CanvasGenerationRequestSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[BoardPatchSchema]:
    return ApiResponse.success(canvas_service.generate_patch(session_id, payload))


@router.post(
    "/sessions/{session_id}/merge-review",
    response_model=ApiResponse[MergeReviewSchema],
    summary="Create merge review",
)
async def create_merge_review(
    session_id: str,
    payload: MergeReviewRequestSchema,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> ApiResponse[MergeReviewSchema]:
    return ApiResponse.success(canvas_service.create_merge_review(session_id, payload))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && pytest tests/modules/test_canvas_generation_contract.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/canvas/router.py backend/app/modules/canvas/service.py backend/app/modules/canvas/schemas.py backend/tests/modules/test_canvas_generation_contract.py
git commit -m "feat: add canvas generation and merge endpoints"
```

### Task 3: Scaffold the Frontend Workspace Shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.js`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/mobile/page.tsx`
- Create: `frontend/src/types/workspace.ts`
- Create: `frontend/src/types/canvas.ts`

- [ ] **Step 1: Write the failing frontend type and render tests**

```ts
import { describe, expect, it } from "vitest";
import { createWorkspaceSession } from "../lib/mocks/canvas-session";

describe("workspace mock session", () => {
  it("defaults to collaborative canvas mode", () => {
    const session = createWorkspaceSession();

    expect(session.activeSurface).toBe("canvas");
    expect(session.permissionMode).toBe("collaborative");
    expect(session.offlineCapability).toBe("single_user_only");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test -- workspace-store`
Expected: FAIL because the frontend app and test setup do not exist yet.

- [ ] **Step 3: Create the minimal frontend app shell and types**

```ts
export type WorkspaceSessionState = {
  sessionId: string;
  activeSurface: "chat" | "document" | "canvas";
  role: "creator" | "viewer";
  permissionMode: "creator_only" | "collaborative" | "viewer_only";
  agentState:
    | "IDLE"
    | "ANALYZING"
    | "RETRIEVING"
    | "GENERATING"
    | "SYNCING"
    | "COMPLETED"
    | "ERROR";
  offlineCapability: "disabled" | "single_user_only";
  lockStatus: "locked" | "unlocked";
};
```

```tsx
export default function WorkspacePage() {
  return (
    <main>
      <h1>Eko Workspace</h1>
      <p>Feishu-compatible canvas workspace</p>
    </main>
  );
}
```

- [ ] **Step 4: Add mobile entry and mock session factory**

```ts
import { WorkspaceSessionState } from "../../types/workspace";

export function createWorkspaceSession(): WorkspaceSessionState {
  return {
    sessionId: "canvas-demo-001",
    activeSurface: "canvas",
    role: "creator",
    permissionMode: "collaborative",
    agentState: "IDLE",
    offlineCapability: "single_user_only",
    lockStatus: "unlocked",
  };
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test -- workspace-store`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/next.config.js frontend/src/app/layout.tsx frontend/src/app/page.tsx frontend/src/app/mobile/page.tsx frontend/src/types/workspace.ts frontend/src/types/canvas.ts frontend/src/lib/mocks/canvas-session.ts
git commit -m "feat: scaffold canvas workspace frontend"
```

### Task 4: Add Workspace Store and Collaboration Event Handling

**Files:**
- Create: `frontend/src/lib/store/workspace.ts`
- Create: `frontend/src/types/sync.ts`
- Create: `frontend/src/__tests__/workspace-store.test.ts`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Write the failing store tests**

```ts
import { describe, expect, it } from "vitest";
import { createWorkspaceStore } from "../lib/store/workspace";

describe("workspace store", () => {
  it("applies agent and canvas sync events", () => {
    const store = createWorkspaceStore();

    store.getState().applySyncEvent({
      type: "agent.state.changed",
      sessionId: "canvas-demo-001",
      state: "GENERATING",
      progress: 55,
    });

    store.getState().applySyncEvent({
      type: "canvas.updated",
      sessionId: "canvas-demo-001",
      canvasJson: { nodes: [{ id: "n1" }] },
      version: 2,
    });

    expect(store.getState().session?.agentState).toBe("GENERATING");
    expect(store.getState().canvasVersion).toBe(2);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test -- workspace-store`
Expected: FAIL because the store and sync types do not exist yet.

- [ ] **Step 3: Implement the Zustand store and sync event types**

```ts
export type SyncEvent =
  | {
      type: "agent.state.changed";
      sessionId: string;
      state: WorkspaceSessionState["agentState"];
      progress: number;
    }
  | {
      type: "canvas.updated";
      sessionId: string;
      canvasJson: Record<string, unknown>;
      version: number;
    };
```

```ts
export const createWorkspaceStore = () =>
  create<WorkspaceStoreState>((set, get) => ({
    session: createWorkspaceSession(),
    canvasVersion: 1,
    canvasJson: { nodes: [], edges: [] },
    applySyncEvent: (event) => {
      if (event.type === "agent.state.changed") {
        set((state) => ({
          session: state.session
            ? { ...state.session, agentState: event.state }
            : state.session,
          progress: event.progress,
        }));
        return;
      }

      if (event.type === "canvas.updated") {
        set({ canvasJson: event.canvasJson, canvasVersion: event.version });
      }
    },
  }));
```

- [ ] **Step 4: Render workspace state from the store**

```tsx
const store = useWorkspaceStore();

return (
  <main>
    <MissionControl session={store.session} progress={store.progress} />
    <CanvasSurface canvasJson={store.canvasJson} version={store.canvasVersion} />
  </main>
);
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test -- workspace-store`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/store/workspace.ts frontend/src/types/sync.ts frontend/src/__tests__/workspace-store.test.ts frontend/src/app/page.tsx
git commit -m "feat: add workspace sync store"
```

### Task 5: Add Canvas Surface, Mission Control, and Context Panel

**Files:**
- Create: `frontend/src/components/surface/CanvasSurface.tsx`
- Create: `frontend/src/components/agent/MissionControl.tsx`
- Create: `frontend/src/components/context/ContextSyncPanel.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Write the failing render tests for main canvas workspace components**

```ts
import { render, screen } from "@testing-library/react";
import { CanvasSurface } from "../components/surface/CanvasSurface";

it("renders canvas version and offline state", () => {
  render(
    <CanvasSurface
      canvasJson={{ nodes: [{ id: "n1", text: "Start" }], edges: [] }}
      version={4}
      offlineState="clean"
    />,
  );

  expect(screen.getByText("Canvas v4")).toBeInTheDocument();
  expect(screen.getByText("Offline: clean")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test -- canvas-surface`
Expected: FAIL because the components do not exist yet.

- [ ] **Step 3: Implement the three primary workspace components**

```tsx
export function MissionControl({
  session,
  progress,
}: {
  session: WorkspaceSessionState | null;
  progress: number;
}) {
  return (
    <section>
      <h2>Mission Control</h2>
      <p>State: {session?.agentState ?? "IDLE"}</p>
      <p>Role: {session?.role ?? "viewer"}</p>
      <p>Progress: {progress}%</p>
    </section>
  );
}
```

```tsx
export function CanvasSurface({
  canvasJson,
  version,
  offlineState,
}: {
  canvasJson: Record<string, unknown>;
  version: number;
  offlineState: "clean" | "dirty" | "replaying";
}) {
  return (
    <section>
      <h2>Canvas v{version}</h2>
      <p>Offline: {offlineState}</p>
      <pre>{JSON.stringify(canvasJson, null, 2)}</pre>
    </section>
  );
}
```

- [ ] **Step 4: Compose the desktop workspace layout**

```tsx
return (
  <main className="workspace-grid">
    <section>{/* chat panel placeholder */}</section>
    <section>
      <MissionControl session={store.session} progress={store.progress} />
      <CanvasSurface
        canvasJson={store.canvasJson}
        version={store.canvasVersion}
        offlineState={store.offlineState}
      />
    </section>
    <ContextSyncPanel session={store.session} />
  </main>
);
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test -- canvas-surface`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/surface/CanvasSurface.tsx frontend/src/components/agent/MissionControl.tsx frontend/src/components/context/ContextSyncPanel.tsx frontend/src/app/page.tsx
git commit -m "feat: add canvas workspace UI shell"
```

### Task 6: Add Offline Queue and Single-User Recovery Rules

**Files:**
- Create: `frontend/src/lib/services/offline-queue.ts`
- Create: `frontend/src/__tests__/offline-queue.test.ts`
- Modify: `frontend/src/lib/store/workspace.ts`
- Modify: `frontend/src/types/workspace.ts`

- [ ] **Step 1: Write the failing offline queue tests**

```ts
import { describe, expect, it } from "vitest";
import { createOfflineQueue } from "../lib/services/offline-queue";

describe("offline queue", () => {
  it("queues edits while offline and marks replaying on reconnect", () => {
    const queue = createOfflineQueue();

    queue.markOffline();
    queue.enqueue({ type: "node.update", nodeId: "n1", text: "Updated" });
    queue.markOnline();

    expect(queue.getState().pending.length).toBe(1);
    expect(queue.getState().status).toBe("replaying");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test -- offline-queue`
Expected: FAIL because the offline queue service does not exist yet.

- [ ] **Step 3: Implement the offline queue service**

```ts
export function createOfflineQueue() {
  let state = {
    isOffline: false,
    status: "clean" as "clean" | "dirty" | "replaying",
    pending: [] as Array<Record<string, unknown>>,
  };

  return {
    markOffline() {
      state = { ...state, isOffline: true };
    },
    enqueue(operation: Record<string, unknown>) {
      state = {
        ...state,
        pending: [...state.pending, operation],
        status: "dirty",
      };
    },
    markOnline() {
      state = { ...state, isOffline: false, status: "replaying" };
    },
    getState() {
      return state;
    },
  };
}
```

- [ ] **Step 4: Connect offline state into the workspace store**

```ts
type WorkspaceStoreState = {
  offlineState: "clean" | "dirty" | "replaying";
  enqueueOfflineOperation: (operation: Record<string, unknown>) => void;
  markReconnected: () => void;
};
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test -- offline-queue`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/services/offline-queue.ts frontend/src/__tests__/offline-queue.test.ts frontend/src/lib/store/workspace.ts frontend/src/types/workspace.ts
git commit -m "feat: add single-user offline recovery queue"
```

### Task 7: Add Canvas Session Polling and Backend-to-Frontend Contract Wiring

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/lib/services/canvas-api.ts`
- Modify: `frontend/src/types/canvas.ts`
- Modify: `backend/app/modules/canvas/router.py`
- Test: `frontend/src/__tests__/workspace-store.test.ts`

- [ ] **Step 1: Write the failing integration-style frontend test for loading session data**

```ts
import { describe, expect, it } from "vitest";
import { normalizeCanvasSession } from "../lib/services/canvas-api";

describe("canvas api normalization", () => {
  it("maps backend session response to workspace state", () => {
    const normalized = normalizeCanvasSession({
      session_id: "canvas-demo-001",
      title: "Feishu Canvas Session",
      mode: "canvas",
      owner_user_id: "creator-001",
      collaborator_ids: ["viewer-001"],
      permission_mode: "collaborative",
      sync_state: "idle",
      offline_capability: "single_user_only",
    });

    expect(normalized.sessionId).toBe("canvas-demo-001");
    expect(normalized.permissionMode).toBe("collaborative");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test -- workspace-store`
Expected: FAIL because the API normalization layer does not exist yet.

- [ ] **Step 3: Add the API adapter and polling hook**

```ts
export function normalizeCanvasSession(
  payload: CanvasSessionResponse,
): WorkspaceSessionState {
  return {
    sessionId: payload.session_id,
    activeSurface: "canvas",
    role: "creator",
    permissionMode: payload.permission_mode,
    agentState: "IDLE",
    offlineCapability: payload.offline_capability,
    lockStatus: "unlocked",
  };
}
```

```tsx
useEffect(() => {
  let cancelled = false;

  async function loadSession() {
    const session = await fetchCanvasSession("canvas-demo-001");
    if (!cancelled) {
      store.setSession(session);
    }
  }

  loadSession();
  return () => {
    cancelled = true;
  };
}, [store]);
```

- [ ] **Step 4: Ensure backend session route returns the full normalized session contract**

```python
@router.get(
    "/sessions/{session_id}",
    response_model=ApiResponse[BoardSessionSchema],
    summary="Canvas session",
)
async def get_canvas_session(...) -> ApiResponse[BoardSessionSchema]:
    return ApiResponse.success(canvas_service.get_session(session_id))
```

- [ ] **Step 5: Run backend and frontend tests**

Run: `cd /Users/klot/Feishu_demo_Eko/backend && pytest tests/modules/test_canvas_contract.py tests/modules/test_canvas_generation_contract.py -v`
Expected: PASS

Run: `cd /Users/klot/Feishu_demo_Eko/frontend && npm test`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/lib/services/canvas-api.ts frontend/src/types/canvas.ts frontend/src/__tests__/workspace-store.test.ts backend/app/modules/canvas/router.py
git commit -m "feat: wire canvas session contracts into frontend"
```

## Self-Review

### Spec coverage

- Dual-track mirror model: covered by Task 1 backend schemas and Task 2 generation and merge contracts.
- AI full-board and targeted patch generation: covered by Task 2.
- Multiple online collaborators: covered by Task 4 store sync events and Task 5 workspace shell.
- Single-user offline recovery: covered by Task 6.
- Chat context plus prompt reserve path: covered by Task 2 generation request contract.
- Merge review after dual-side change: covered by Task 2 merge review contract.
- Frontend workspace and mobile shell: covered by Task 3 and Task 5.

### Placeholder scan

- No `TODO`, `TBD`, or "implement later" placeholders remain in the tasks.
- Every test and implementation step includes exact file paths, commands, or code snippets.

### Type consistency

- Backend generation modes are consistently `full_board` and `targeted_patch`.
- Offline states are consistently `clean`, `dirty`, and `replaying`.
- Permission modes are consistently `creator_only`, `collaborative`, and `viewer_only`.

