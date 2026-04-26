# Feishu Canvas Compatibility Design

Date: 2026-04-26
Topic: Feishu-compatible canvas module for Eko
Status: Draft approved in conversation, written for review

## 1. Goal

Build a canvas module inside Eko that can:

- import and preserve Feishu canvas content as an original source board;
- let the model generate a board from chat context plus user requirements;
- let users continue editing the generated board;
- support multiple people editing online at the same time;
- support single-user offline editing with recovery after reconnect;
- detect conflicts between Feishu-side changes and Eko-side changes, then require human merge confirmation.

The module must support dual-track compatibility rather than a one-way import/export flow.

## 2. Product Positioning

The canvas module is not only a renderer. It is a collaborative working surface for:

- AI-first board generation;
- user-directed refinement;
- online co-editing;
- sync with a Feishu-origin board;
- reviewable merge decisions when both sides change.

This module should fit the existing Eko workflow where tasks begin from conversation context and continue inside the dedicated workspace.

## 3. Core Design Decision

Use a dual-track mirror model:

- `Feishu Source Board`
  - the original board imported from or linked to Feishu;
  - preserves source identity, source version, raw payload, and compatibility metadata;
  - acts as the external truth for provenance and outbound sync.

- `Eko Working Board`
  - the editable working copy inside Eko;
  - used for AI generation, user editing, collaboration, and offline work;
  - uses an operation-friendly document model suitable for incremental sync.

- `Board Mapping Layer`
  - keeps track of element-level relationships between Feishu and Eko;
  - records which Eko elements came from source import, AI generation, user edits, or merge resolution;
  - prevents whole-board overwrite behavior.

- `Merge Review Layer`
  - required when Feishu and Eko both change overlapping areas;
  - presents conflicts explicitly rather than auto-overwriting.

This design is preferred over Feishu-native-only or Eko-only approaches because it simultaneously preserves source compatibility, AI flexibility, and editable collaboration.

## 4. User Experience Flow

### 4.1 Import or Open

The user opens a Feishu-linked canvas task from the Eko workspace.

System behavior:

- read Feishu board metadata and raw content;
- create or refresh `Feishu Source Board`;
- create or update `Eko Working Board`;
- initialize element mappings and version pointers.

### 4.2 AI Generation

The user asks Eko to generate a board based on:

- chat context;
- explicit user requirement;
- current board context, if any;
- generation mode.

Generation mode supports:

- `full_board`: generate an initial full-board draft;
- `targeted_patch`: update only a selected region or set of nodes.

The recommended generation UX is mixed mode:

1. generate a full-board first draft from conversation plus requirements;
2. let the user select regions and ask for local refinement later.

### 4.3 User Editing

Users can directly edit the `Eko Working Board` after AI generation:

- move and group nodes;
- rewrite text;
- connect nodes;
- add new elements;
- remove or merge sections.

AI and manual edits must share the same change system so that history, undo, merge, and outbound sync stay consistent.

### 4.4 Online Collaboration

Multiple users may edit the `Eko Working Board` together while online.

Requirements:

- low-latency incremental synchronization;
- presence awareness for collaborators;
- no whole-document replacement during normal editing;
- compatible history for user operations and AI patches.

### 4.5 Offline Recovery

Offline editing is supported only for the single-user case in MVP.

When the user disconnects:

- editing continues against the local working copy;
- local changes are stored as incremental operations plus local snapshots.

When connectivity returns:

- replay local offline operations into the cloud working board;
- compare cloud changes and Feishu-side changes that occurred during the offline window;
- if both sides changed overlapping content, enter merge review.

### 4.6 Merge Review

When Feishu and Eko both change relevant content:

- do not auto-overwrite by default;
- show explicit conflict units such as renamed nodes, changed text, added or removed elements, and structural differences;
- let the user choose Feishu version, Eko version, or a new merged result.

For text-only conflicts, the system may offer AI-assisted merge suggestions, but final submission remains user-confirmed.

## 5. Chat Context and Prompt Pipeline

The canvas module must reserve a structured input path for future chat-history integration. The current design does not depend on the real chat-ingest implementation, but it must expose stable interfaces for it.

### 5.1 Input Contract

The generation pipeline should accept a single normalized payload:

- `chat_context`
- `user_prompt`
- `board_context`
- `generation_mode`
- `selection_context`
- `session_metadata`

### 5.2 Prompt Strategy

Use:

- a default system template maintained by the backend;
- user-supplied extra instruction appended for each generation request.

This supports stable baseline behavior plus flexible business-specific refinement.

Examples of user-added instruction:

- "turn this into a product roadmap"
- "rewrite this area as a timeline"
- "expand this section into an execution plan"

### 5.3 Output Shape

The model should not output screenshots or unstructured prose as the primary result.

Instead, it should output a `Board Patch`:

- for `full_board`, a patch that creates the initial board graph and layout hints;
- for `targeted_patch`, a patch scoped to the selected region.

This keeps model output compatible with collaboration, versioning, merge, and export.

## 6. System Architecture

Split the solution into five modules.

### 6.1 Canvas Editor

Responsibilities:

- render and edit the `Eko Working Board`;
- apply local edits and remote updates;
- expose selection state for targeted AI generation;
- support online collaboration presence;
- support local offline persistence.

### 6.2 AI Generation Pipeline

Responsibilities:

- normalize generation inputs;
- assemble prompt from chat context, board context, and user instruction;
- call the model for full-board or targeted patch generation;
- validate patch structure before applying it to the working board.

### 6.3 Board Sync Engine

Responsibilities:

- import Feishu board data;
- maintain board-element mappings;
- detect source-board changes;
- prepare outbound updates back to Feishu;
- detect merge conditions and create merge review tasks.

### 6.4 Session and Permission Layer

Responsibilities:

- session ownership and collaboration membership;
- creator/editor/viewer permissions;
- lock state during protected operations if needed;
- offline eligibility checks for the single-user case.

### 6.5 Board History Service

Responsibilities:

- snapshots;
- operation log storage;
- AI patch records;
- merge audit trail;
- recovery points.

## 7. Data Model

### 7.1 `BoardSession`

Fields should include:

- `session_id`
- `workspace_id`
- `title`
- `status`
- `active_surface`
- `owner_user_id`
- `collaborator_ids`
- `permission_mode`
- `sync_state`
- `offline_capability`
- `created_at`
- `updated_at`

### 7.2 `FeishuSourceBoard`

Fields should include:

- `source_board_id`
- `session_id`
- `feishu_file_token` or equivalent source reference
- `source_version`
- `raw_payload`
- `imported_at`
- `last_synced_at`
- `sync_cursor`

### 7.3 `EkoWorkingBoard`

Fields should include:

- `working_board_id`
- `session_id`
- `document_type`
- `crdt_document`
- `latest_snapshot`
- `latest_version`
- `last_ai_patch_id`
- `offline_state`
- `updated_at`

### 7.4 `BoardElementMapping`

Fields should include:

- `mapping_id`
- `session_id`
- `source_element_id`
- `working_element_id`
- `mapping_status`
- `origin_type`
- `created_at`
- `updated_at`

`origin_type` should distinguish:

- imported from Feishu;
- created by AI;
- created by user;
- produced by merge.

### 7.5 `BoardChange`

Fields should include:

- `change_id`
- `session_id`
- `change_type`
- `actor_type`
- `actor_id`
- `target_scope`
- `payload`
- `base_version`
- `result_version`
- `created_at`

`change_type` should cover:

- user edit;
- AI patch;
- source import;
- sync export;
- conflict detected;
- merge resolved;
- offline replay.

## 8. Synchronization Model

### 8.1 Working Board Sync

The `Eko Working Board` should use CRDT-style incremental synchronization instead of full JSON replacement.

Why:

- multiple users may edit at once;
- AI patches need to coexist with manual edits;
- undo, replay, and offline recovery need operation history.

### 8.2 Feishu Sync

Feishu sync should behave as a translation layer, not as the primary live collaboration engine.

The sync engine should:

- read source-board versions from Feishu;
- translate working-board changes into Feishu-compatible updates where possible;
- maintain version checkpoints;
- stop for review when lossy mapping or direct conflicts are detected.

### 8.3 Conflict Policy

Default policy is manual merge confirmation.

The system should not silently choose Feishu-first or Eko-first when both sides changed overlapping content.

## 9. Collaboration and Offline Rules

### 9.1 Online Collaboration

Supported in MVP:

- multiple online editors;
- presence indicators;
- shared current state;
- AI patch application into the same working board.

### 9.2 Offline Editing

Supported in MVP:

- only one active offline editor;
- local operation queue;
- reconnect replay;
- merge review if remote changes occurred meanwhile.

Not supported in MVP:

- multiple concurrent offline editors;
- automatic multi-offline merge without user review.

## 10. MVP Scope

### In Scope

- create `FeishuSourceBoard` from imported Feishu board content;
- create editable `EkoWorkingBoard`;
- generate full-board draft from chat-context placeholder input plus user prompt;
- allow direct user editing on the working board;
- allow multiple users to collaborate online;
- support targeted AI patch generation for selected regions;
- support single-user offline editing and reconnect recovery;
- detect dual-side changes and create merge review;
- track board history and change origin.

### Out of Scope

- guaranteed lossless support for every advanced Feishu-specific element type in v1;
- automatic live two-way sync with no review boundary;
- multi-user offline conflict-free recovery in v1;
- final organization-grade permission matrix in v1;
- production-grade chat-ingest implementation in this phase.

## 11. Technical Direction

Frontend should continue to align with the existing workspace approach in the repository:

- Next.js workspace shell;
- dedicated canvas surface;
- session-aware collaboration state;
- workspace-oriented permission and sync indicators.

Backend should extend the current FastAPI `canvas` skeleton into:

- session endpoints;
- working board state endpoints;
- AI generation endpoints;
- sync and merge endpoints;
- collaboration state endpoints.

Redis or equivalent real-time infrastructure can carry collaboration broadcasts, but persistent board truth must live in the versioned working document and change log.

## 12. Risks and Constraints

### 12.1 Format Compatibility Risk

Feishu board internals may include element types or semantics that are not perfectly editable inside Eko. The mapping layer must explicitly mark unsupported or partially supported structures instead of pretending to preserve them.

### 12.2 Merge Complexity Risk

Manual merge is the correct default, but the review UI can still become hard to understand if conflict units are too coarse. Conflict presentation should stay element-level whenever possible.

### 12.3 Offline Complexity Risk

Offline recovery becomes much harder once multiple users edit offline independently. MVP should keep the rule strict: single-user offline only.

### 12.4 Model Output Risk

If model output is too free-form, board patches become unreliable. The generation pipeline must validate schema and reject malformed patches before applying them.

## 13. Acceptance Criteria for the Design

The design is successful if the implementation can eventually demonstrate:

- a Feishu-origin board can be imported into Eko;
- a working copy can be generated and edited;
- AI can generate a first draft from chat context plus prompt;
- users can manually refine the board afterward;
- multiple users can collaborate online on the working copy;
- a single user can continue editing offline and recover after reconnect;
- Feishu-side and Eko-side conflicting edits trigger merge review instead of silent overwrite.
