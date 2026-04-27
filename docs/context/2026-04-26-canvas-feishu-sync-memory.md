# Canvas Feishu Sync Memory

Date: 2026-04-26

## Current backend status

- Feishu docx import is wired through:
  - document resolve
  - document blocks pagination
  - whiteboard discovery via `block_type=43`
  - whiteboard nodes fetch
- Canvas session flow is implemented:
  - import Feishu document into session
  - local working board edits
  - AI generate/apply patch
  - refresh with conflict detection
  - merge review / resolve
  - export
  - publish

## Important publish behavior

- `POST /api/v1/feishu/boards/publish`
- `POST /api/v1/canvas/sessions/{session_id}/publish-feishu-board`
- If `FEISHU_WHITEBOARD_PUBLISH_ENDPOINT_TEMPLATE` is unset:
  - publish stays in `adapter_only`
- If configured:
  - publish calls real Feishu `POST /board/v1/whiteboards/{whiteboard_id}/nodes`
  - if `source_board.metadata.theme` exists, it also calls `POST /update_theme`
  - if target whiteboard already has nodes, publish refuses with:
    - `mode=upstream`
    - `accepted=false`
    - `reason=target_board_not_empty`

## Important model constraint

- The system originally normalized whiteboard nodes down to `{id, text}` only.
- This blocked realistic upstream publish and future sync fidelity.
- Current improvement:
  - imported whiteboard nodes now preserve original Feishu node fields
  - normalization now copies the source node and guarantees unified `id` and `text`
  - working snapshot therefore keeps richer node shape too

## Why this matters

- Real publish can now reuse more native node structure instead of always degrading to generated `text_shape`.
- Future work on update/delete/diff sync will have better source fidelity.

## Still missing

- No confirmed Feishu node update/delete API is integrated yet.
- Current upstream publish is safe-create only, not full overwrite sync.
- Connector handling is still mixed:
  - simplified `edges`
  - richer native connector nodes if source/import provides them
- Working board schema is still loosely typed `dict` data, not a first-class Feishu node model.

## Best next step

- Introduce an internal richer board node contract for Canvas working snapshots:
  - distinguish native node objects from simplified fallback nodes
  - make connector handling consistent
  - prepare for future diff-based sync instead of create-only publish

## Verification snapshot

- Relevant test suite last known status:
  - `backend/tests/modules/test_canvas_contract.py`
  - `backend/tests/modules/test_canvas_generation_contract.py`
  - `backend/tests/modules/test_canvas_persistence_contract.py`
  - `backend/tests/modules/test_feishu_document_contract.py`
  - `backend/tests/modules/test_feishu_module_contract.py`
  - `backend/tests/modules/test_feishu_canvas_adapter_contract.py`
- Result:
  - `60 passed`
