# Feishu Demo Eko

Eko is a Feishu-native AI office workspace demo. It combines a Next.js web workspace, a FastAPI backend, Feishu integration, Agent orchestration, RAG retrieval, Bitable structured data, Redis realtime events, and AI PPT / document / canvas generation.

The project is intended to demonstrate an end-to-end office workflow: users can mention Eko in a Feishu group or open the web workspace, ask for a document, PPT, board, or answer, and the system will route the intent, retrieve context, plan executable steps, call the right tools, stream progress, and archive results back into the Feishu ecosystem.

## Core Capabilities

- Feishu OAuth login, event callback handling, and long-connection listener.
- Agent chat with tool-level intent routing for chat, document, PPT, and board tasks.
- LangGraph-backed runtime for context loading, retrieval, planning, and tool execution.
- RAG knowledge base with document ingestion, embeddings, and pgvector similarity search.
- Bitable OpenAPI integration for structured context retrieval and artifact archiving.
- AI PPT generation and editing through the built-in `vendor/ppt-master` runtime.
- Document generation, Feishu document sync, and tldraw / Feishu board workflows.
- Redis Pub/Sub realtime event bus for Agent progress, session updates, and sync state.
- Next.js workspace UI for sessions, knowledge, documents, team, settings, and profile pages.

## Architecture

```text
Feishu group / card / web workspace
        |
        v
Next.js frontend  <---- realtime session events ---->  FastAPI backend
                                                        |
                                                        v
                              RouterAgent -> AgentRuntime -> PlannerAgent
                                   |           |              |
                                   |           v              v
                                   |       RAG / Bitable   Tool Registry
                                   |                          |
                                   v                          v
                         Document / AIPPT / Canvas / Sync / Archive
                                                        |
                                                        v
                                    PostgreSQL + pgvector, Redis, Feishu OpenAPI
```

Agent turns are prepared through a runtime flow of:

```text
context -> retrieval -> planner -> tool_execute
```

RAG retrieval currently uses embeddings plus pgvector cosine-distance ordering. In the Agent flow, the retriever defaults to RAG Top-4 and Bitable Top-4, then keeps at most 8 merged context chunks for planning and tool execution. There is no separate reranker model in the current implementation.

## Repository Layout

```text
backend/           FastAPI application, Agent services, Feishu/Bitable/RAG/AIPPT modules
frontend/          Next.js workspace application
docs/              Integration notes and defense materials
vendor/ppt-master/ Built-in AI PPT conversion runtime
API.md             API contract draft
ARCHITECTURE.md    Architecture notes
PRD.md             Product requirement notes
TEAM.md            Team notes
```

Runtime data, generated PPT files, local dependencies, caches, uploaded files, and internal temporary outputs are intentionally excluded from version control.

## Requirements

- Node.js 20+
- Python 3.12+
- PostgreSQL 14+ with pgvector enabled
- Redis 7+
- Feishu app credentials for live Feishu OAuth, events, document, board, and Bitable flows

## Backend Setup

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` before starting the service. The most important sections are:

- PostgreSQL and Redis connection settings.
- Feishu app credentials and callback settings.
- Agent model and embedding model settings.
- Bitable enable/archive flags and workspace defaults.
- AI PPT model, storage, queue, and image generation settings.

Start the backend:

```sh
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend exposes APIs under `/api/v1` and can also mount the frontend build/static directory when configured.

## Frontend Setup

```sh
cd frontend
npm install
npm run dev
```

The frontend development server runs on port `3002` by default.

From the repository root you can also run:

```sh
npm run dev
npm run build
npm run start
npm run lint
```

These root scripts delegate to the frontend package.

## Important Configuration

### Agent and RAG

```env
AGENT_MODEL=deepseek-v4-flash
AGENT_API_BASE=https://api.deepseek.com
AGENT_EMBEDDING_MODEL=Qwen3-Embedding-8B
AGENT_EMBEDDING_API_BASE=https://ai.gitee.com/v1
RAG_EMBEDDING_DIMENSIONS=1024
RAG_CHUNK_SIZE=450
RAG_CHUNK_OVERLAP=80
```

If no valid embedding API key is configured, the backend falls back to a deterministic local embedding client for tests and keyless development.

### Bitable

```env
BITABLE_ENABLED=true
BITABLE_ARCHIVE_ENABLED=false
BITABLE_DEFAULT_WORKSPACE_ID=Feishu_demo_Eko
BITABLE_QUERY_LIMIT=8
```

Bitable is used in two ways: as a structured context source for Agent generation, and as an optional archive target for completed docx, ppt, and board artifacts. See `docs/bitable-openapi-integration.md` for integration details.

### Redis

Redis is used as both an infrastructure dependency and a realtime event bus. The backend publishes Agent progress, session state, Feishu sync updates, and AI PPT queue information through Redis-backed flows.

```env
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### AI PPT

```env
AIPPT_MODEL=deepseek-v4-flash
AIPPT_STORAGE_DIR=storage/aippt
AIPPT_VENDOR_DIR=vendor/ppt-master
AIPPT_REDIS_QUEUE_ENABLED=true
```

Generated files and intermediate PPT projects are stored under `backend/storage/aippt` by default and should not be committed.

## Test and Verification

Run backend tests:

```sh
cd backend
python -m pytest
```

Run a narrower smoke set:

```sh
cd backend
python -m pytest \
  tests/test_agent_intent_routing.py \
  tests/test_agent_event_channels.py \
  tests/test_bitable_service.py \
  tests/test_feishu_full_flow.py
```

Check Python import/compile health:

```sh
cd backend
python -m compileall app
```

Run frontend checks:

```sh
cd frontend
npm run lint
npm run build
```

## Development Notes

- `frontend/src/components/knowledge/BitableSourcesPanel.tsx` contains the Bitable source configuration UI.
- `backend/app/modules/agent/service.py` contains intent routing, current-artifact handling, and high-level Agent execution.
- `backend/app/modules/agent/runtime.py` contains the LangGraph-backed runtime.
- `backend/app/modules/rag/` contains embedding, ingestion, splitting, and pgvector search.
- `backend/app/modules/bitable/` contains Feishu Bitable OpenAPI integration.
- `backend/app/modules/aippt/` contains AI PPT job creation, rendering, and export orchestration.
- `backend/app/modules/sync/` and Redis-backed managers handle realtime session state.

## Git and Artifact Hygiene

Do not commit:

- `.env`, `.env.local`, secrets, credentials, or local tunnel URLs.
- Python virtual environments, `node_modules`, `.next`, caches, and test artifacts.
- `backend/storage`, `backend/runtime`, uploaded files, generated PPT/media outputs.
- Temporary screenshots, local debug exports, and machine-specific files.

Keep committed:

- Source code, tests, package manifests, lockfiles, `.env.example`, docs, and reusable scripts.

## Useful Docs

- `API.md`
- `ARCHITECTURE.md`
- `PRD.md`
- `docs/bitable-openapi-integration.md`
