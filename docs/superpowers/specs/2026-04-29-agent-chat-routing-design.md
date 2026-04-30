# Agent Chat Routing Design

## Goal

Provide one backend endpoint that a single page can call for basic Agent chat and direct routing to AIDocx, AIPPT, and AI Board.

## Scope

- Add `POST /api/v1/agent/chat`.
- Use the existing Volcengine `LLMClient` for intent classification and basic chat replies.
- Route intents to:
  - `chat`: Volcengine reply.
  - `docx`: `DocumentService.generate_document`.
  - `ppt`: `PptService.create_deck`.
  - `board`: `CanvasService.create_board_task` followed by `CanvasService.run_board_task`.
- Preserve the existing AI Board behavior: board execution uses the Feishu-first board pipeline already implemented in `BoardGenerateService`.
- Return a stable response shape with `intent`, `status`, `message`, and optional `artifact`.

## Non-Goals

- No frontend implementation.
- No multiplayer collaboration.
- No new PostgreSQL schema in this step.
- No Feishu document sync changes.
- No multi-step planning agent.

## Failure Behavior

The endpoint should not leak tracebacks to the page. If a routed tool fails, it returns `status="failed"`, the selected `intent`, and an error message.
