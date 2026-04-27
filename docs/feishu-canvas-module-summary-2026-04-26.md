# Feishu Canvas Module Summary

Date: 2026-04-26
Project: `/Users/klot/Feishu_demo_Eko`
Purpose: Summarize the current understanding, completed backend work, and recommended next steps for the Feishu-compatible canvas module.

## 1. Module Positioning

This module is not only a Feishu document parser and not only a frontend canvas.

Its intended product role is:

- use Feishu content as an external source of truth and compatibility boundary;
- maintain an editable Eko working board as the internal collaboration surface;
- support AI-first board generation from chat context and user prompt;
- support user editing, online co-editing, offline recovery, and merge review;
- avoid whole-board overwrite by tracking element mappings and change history.

The design document describes this as a dual-track mirror model:

- `Feishu Source Board`
- `Eko Working Board`
- `Board Mapping Layer`
- `Merge Review Layer`

Reference:
- [docs/superpowers/specs/2026-04-26-feishu-canvas-compatibility-design.md](/Users/klot/Feishu_demo_Eko/docs/superpowers/specs/2026-04-26-feishu-canvas-compatibility-design.md)

## 2. What This Phase Is Actually Doing

The current priority is not the full product surface and not the full frontend.

The current priority is to establish a reliable backend-only source-ingest path:

- `share_url -> document_id/document_token`
- `document_id -> docx blocks`
- `blocks -> whiteboard_id`
- `whiteboard_id -> board nodes`

This path is important because it forms the earliest part of the future `Board Sync Engine`. Without it, the later `Feishu Source Board -> Eko Working Board` flow does not have a stable upstream input.

## 3. Business Interpretation Of The Current Backend Slice

The backend work completed so far belongs to the "source discovery and source read" portion of the full module.

It currently proves that Eko can:

- accept a Feishu document share link;
- resolve the linked Feishu document token;
- fetch document blocks with pagination;
- detect embedded whiteboards inside document blocks;
- fetch the node payload of a discovered whiteboard;
- expose normalized backend responses for testing and later adapter work.

This is still narrower than the full design. It does not yet mean that:

- a persisted `FeishuSourceBoard` has been created;
- an `EkoWorkingBoard` has been initialized from real Feishu nodes;
- AI generation patches are being applied to a working board;
- collaboration, offline replay, merge review, or outbound Feishu sync are complete.

## 4. Completed Work Before This Session

The repository had already reached these milestones:

- Feishu Docx blocks capability was added.
- Upstream source endpoint: `GET /open-apis/docx/v1/documents/:document_id/blocks`
- Backend test route existed: `GET /api/v1/feishu/documents/{document_id}/blocks`
- Blocks pagination was supported across all pages using `page_token` and `has_more`.
- A page-token progression guard was added to avoid pagination loops.
- Whiteboard discovery from blocks was added with:
  - detection rule: `block_type == 43`
  - extracted field: `board.token` as `whiteboard_id`
- Document blocks responses were normalized to include:
  - `document_id`
  - `blocks`
  - `whiteboards`

Important fixes that had already been made:

- default dependency injection no longer silently falls back to a stub client;
- upstream Feishu errors no longer get swallowed and misreported as HTTP 200;
- blocks pagination now protects against repeated or non-advancing page tokens.

## 5. Work Added In This Session

This session added the next narrow source-read step:

- `whiteboard_id -> board nodes`

It also added one aggregate backend entry that bridges:

- `share_url -> document_id -> blocks -> first whiteboard_id -> board nodes`

### 5.1 New Normalized Capability

Added client and service support for:

- fetching whiteboard nodes from Feishu;
- normalizing the nodes payload into a backend schema;
- resolving the first discovered whiteboard from a document and returning its nodes.

### 5.2 New Backend Route

Added a test-oriented route:

- `POST /api/v1/feishu/documents/resolve-whiteboard-nodes`

Expected output shape:

- `document_id`
- `whiteboard_id`
- `block_id`
- `nodes`
- `raw_payload`

### 5.3 Files Updated In This Session

- [backend/app/modules/feishu/client.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/client.py)
- [backend/app/modules/feishu/service.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/service.py)
- [backend/app/modules/feishu/router.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/router.py)
- [backend/app/modules/feishu/schemas.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/schemas.py)
- [backend/app/modules/feishu/dependencies.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/dependencies.py)
- [backend/app/config.py](/Users/klot/Feishu_demo_Eko/backend/app/config.py)
- [backend/tests/modules/test_feishu_document_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_feishu_document_contract.py)
- [docs/superpowers/plans/2026-04-26-feishu-whiteboard-nodes-bridge.md](/Users/klot/Feishu_demo_Eko/docs/superpowers/plans/2026-04-26-feishu-whiteboard-nodes-bridge.md)

## 6. Failure Cases Covered By Tests

The latest test additions intentionally focused on failure behavior as well as success behavior.

Covered cases:

- whiteboard blocks with missing `board.token` are ignored rather than treated as valid whiteboards;
- direct whiteboard nodes fetch returns normalized node lists;
- document-to-whiteboard aggregate lookup returns `404` when no usable whiteboard is discovered;
- board nodes upstream failures still surface as explicit `502`;
- existing document resolve and document blocks behavior remain green.

## 7. Current Verification Evidence

The following commands were run after implementation:

```bash
backend/.venv/bin/python -m pytest backend/tests/modules/test_feishu_document_contract.py -q
```

Result:

- `16 passed`

```bash
backend/.venv/bin/python -m pytest backend/tests/modules/test_feishu_document_contract.py backend/tests/modules/test_feishu_module_contract.py backend/tests/modules/test_feishu_canvas_adapter_contract.py -q
```

Result:

- `19 passed`

## 8. Current Architecture Understanding

The repository currently has two related but distinct layers:

### 8.1 `feishu` Module

This is the upstream integration boundary.

Its responsibility is to:

- talk to Feishu APIs;
- normalize upstream responses;
- expose source-side contracts;
- provide read paths for document and whiteboard discovery.

### 8.2 `canvas` Module

This is the internal working-surface boundary.

Its intended responsibility is to:

- store session state;
- represent the `Eko Working Board`;
- track changes, snapshots, and sync-related state;
- eventually host generation, merge, and collaboration flows.

At the moment, the `canvas` side is still more scaffolded than the source-ingest side.

## 9. Important Naming And Modeling Notes

The current codebase already suggests some boundaries that should be preserved:

- `whiteboard_id` is a Feishu-side source identifier and should not be casually merged with generic `board_id`.
- `source_board_id` and `working_board_id` belong to the internal dual-track design and are not the same thing as the source whiteboard token.
- current Feishu whiteboard node payloads may use fields like `node_id` and `title`.
- existing adapter and canvas-side board payloads often assume fields like `id` and `text`.

This means the next adapter stage should not directly assume the source nodes are already in working-board shape.

## 10. What Is Still Missing Relative To The Full Design

The design document envisions a much larger module than the current source-read slice.

Still missing or only partially scaffolded:

- persistent `FeishuSourceBoard` creation from real source payloads;
- initialization of a real `EkoWorkingBoard` from imported Feishu content;
- element-level mapping between source and working elements;
- AI generation pipeline producing validated board patches;
- targeted patch generation for selected regions;
- multi-user online collaboration infrastructure;
- single-user offline operation queue and replay;
- merge review units for dual-side conflicts;
- outbound sync translation back into Feishu-compatible updates.

## 11. Recommended Next Step

The most natural next backend step is:

- add a translation layer from Feishu whiteboard nodes into the internal board/import shape expected by the adapter and canvas flows.

That work should explicitly handle field normalization, especially:

- `node_id -> id`
- `title -> text`
- unsupported Feishu-specific structures
- provenance tagging for imported elements

Recommended order:

1. keep the source-read path stable;
2. build a small adapter that translates Feishu nodes into a normalized internal board shape;
3. initialize a `FeishuSourceBoard` and `EkoWorkingBoard` from that normalized payload;
4. only then expand toward generation, merge, collaboration, and sync.

## 12. Suggested Prompt For The Next Session

If a future session should continue from this exact point, a good starting instruction is:

> Please continue from the existing Feishu document blocks and whiteboard nodes bridge. Do not rebuild the frontend. Next, translate Feishu whiteboard node payloads into the internal board/import shape, and prioritize backend tests for mapping and failure cases.

## 13. Incremental Update: Whiteboard Import Bridge

Completed after the initial summary:

- added a bridge from `share_url -> first whiteboard -> adapter payload`;
- added a backend route `POST /api/v1/feishu/documents/resolve-whiteboard-import`;
- normalized Feishu whiteboard node fields into current adapter-compatible node fields:
  - `node_id -> id`
  - `title -> text`
- returned a full `FeishuBoardAdapterPayloadSchema`, including working-board initialization and identity node mappings;
- verified that the translated payload can be ingested by the current `canvas` repository flow.

Files involved in this follow-up step:

- [backend/app/modules/feishu/service.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/service.py)
- [backend/app/modules/feishu/router.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/router.py)
- [backend/app/modules/feishu/schemas.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/schemas.py)
- [backend/tests/modules/test_feishu_canvas_adapter_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_feishu_canvas_adapter_contract.py)
- [backend/tests/modules/test_feishu_document_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_feishu_document_contract.py)

## 14. Incremental Update: Canvas Session Import Route

Completed after the whiteboard import bridge:

- added a canvas-facing route `POST /api/v1/canvas/sessions/{session_id}/import-feishu-document`;
- this route resolves the Feishu document, discovers the first whiteboard, translates nodes into adapter payload, and ingests the result into the canvas session store;
- the returned payload is `CanvasSessionDetailSchema`, so the backend now exposes a fuller end-to-end test path from Feishu document link to canvas session state.

Files involved in this follow-up step:

- [backend/app/modules/canvas/router.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/canvas/router.py)
- [backend/tests/modules/test_canvas_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_canvas_contract.py)

## 15. Incremental Update: Source Metadata Preservation

Completed after reviewing the implementation against the design document:

- kept the existing import bridge, but made it closer to the dual-track design by preserving explicit source metadata;
- `FeishuBoardSourceSchema` now carries `metadata` for bridge-time provenance;
- document-driven imports now preserve:
  - `share_url`
  - `document_id`
  - `document_token`
  - `whiteboard_id`
  - `block_id`
  - derived `source_version`
  - raw normalized document and whiteboard payload snapshots
- `CanvasRepository.ingest_feishu_board()` now promotes that metadata into `FeishuSourceBoard.source_version` and stores structured source metadata inside `raw_payload`.

Why this matters:

- it better matches the design requirement that `Feishu Source Board` preserve source identity, source version, raw payload, and compatibility metadata;
- it reduces the risk that the current bridge becomes a lossy import path before sync and merge work begins.

Files involved in this follow-up step:

- [backend/app/modules/feishu/schemas.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/schemas.py)
- [backend/app/modules/feishu/service.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/service.py)
- [backend/app/modules/canvas/repository.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/canvas/repository.py)
- [backend/tests/modules/test_feishu_canvas_adapter_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_feishu_canvas_adapter_contract.py)
- [backend/tests/modules/test_canvas_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_canvas_contract.py)

## 16. Incremental Update: Mapping Provenance For Source Import

Completed after the source-metadata step:

- source-imported `element_mappings` now explicitly carry provenance fields instead of only bare IDs;
- each mapping now includes:
  - `origin_type`
  - `mapping_status`
  - `metadata`
- document-driven Feishu imports currently mark imported node mappings as:
  - `origin_type = source_import`
  - `mapping_status = active`
- mapping metadata keeps the minimum source locator set:
  - `document_id`
  - `whiteboard_id`
  - `block_id`
  - source type marker

Why this matters:

- it starts to align the bridge with the design document's `Board Mapping Layer`;
- it makes later sync, merge, and conflict work less lossy because imported working elements already remember where they came from.

Files involved in this follow-up step:

- [backend/app/modules/feishu/schemas.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/schemas.py)
- [backend/app/modules/feishu/service.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/feishu/service.py)
- [backend/tests/modules/test_feishu_canvas_adapter_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_feishu_canvas_adapter_contract.py)
- [backend/tests/modules/test_canvas_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_canvas_contract.py)

## 17. Incremental Update: Persist Element Mappings In Canvas Detail

Completed after the mapping-provenance step:

- `CanvasSessionDetailSchema` now stores `element_mappings` directly;
- `CanvasRepository.ingest_feishu_board()` now persists imported mappings onto the session detail instead of only leaving them inside the import change payload;
- default canvas detail responses return `element_mappings: []` when no imported mapping state exists yet.

Why this matters:

- it moves the implementation closer to the design document's dedicated `Board Mapping Layer`;
- later sync and merge work can read current mapping state directly from the session detail instead of reconstructing it from change history.

Files involved in this follow-up step:

- [backend/app/modules/canvas/schemas.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/canvas/schemas.py)
- [backend/app/modules/canvas/repository.py](/Users/klot/Feishu_demo_Eko/backend/app/modules/canvas/repository.py)
- [backend/tests/modules/test_canvas_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_canvas_contract.py)
- [backend/tests/modules/test_feishu_canvas_adapter_contract.py](/Users/klot/Feishu_demo_Eko/backend/tests/modules/test_feishu_canvas_adapter_contract.py)
