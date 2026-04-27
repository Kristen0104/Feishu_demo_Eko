# Feishu Whiteboard Nodes Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a narrow backend-only read path that resolves a Feishu document share URL into the first discovered whiteboard and returns that whiteboard's node payload.

**Architecture:** Extend the existing `feishu` module rather than the stub import/export adapter. The new path will reuse the existing document resolve and document blocks flow, add a whiteboard nodes fetcher in `FeishuClient`, and expose a test-oriented route that returns normalized `document_id`, `whiteboard_id`, and `nodes`.

**Tech Stack:** FastAPI, Pydantic, Pytest, existing `FeishuClient` HTTP transport and error mapping.

---

## File Structure

- Modify: `backend/app/modules/feishu/client.py`
- Modify: `backend/app/modules/feishu/service.py`
- Modify: `backend/app/modules/feishu/router.py`
- Modify: `backend/app/modules/feishu/schemas.py`
- Modify: `backend/app/modules/feishu/dependencies.py`
- Modify: `backend/app/config.py`
- Modify: `backend/tests/modules/test_feishu_document_contract.py`

### Task 1: Add Contract Tests For Whiteboard Nodes Lookup

**Files:**
- Modify: `backend/tests/modules/test_feishu_document_contract.py`
- Test: `backend/tests/modules/test_feishu_document_contract.py`

- [ ] **Step 1: Write the failing tests**
- [ ] **Step 2: Run the focused pytest selection and confirm the new tests fail for the expected missing behavior**
- [ ] **Step 3: Cover one success case and these failures: no usable whiteboard discovered, missing `board.token` ignored, upstream board nodes failure bubbles as `502`**

### Task 2: Implement Whiteboard Nodes Client And Aggregation

**Files:**
- Modify: `backend/app/modules/feishu/client.py`
- Modify: `backend/app/modules/feishu/service.py`
- Modify: `backend/app/modules/feishu/schemas.py`
- Modify: `backend/app/modules/feishu/dependencies.py`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add schema types for normalized whiteboard nodes payload**
- [ ] **Step 2: Add a configurable whiteboard nodes endpoint template**
- [ ] **Step 3: Implement `get_whiteboard_nodes(whiteboard_id)` in `FeishuClient`**
- [ ] **Step 4: Implement a service-level aggregator that performs `share_url -> document_id -> blocks -> first whiteboard -> nodes`**

### Task 3: Expose And Verify The Backend Read Route

**Files:**
- Modify: `backend/app/modules/feishu/router.py`
- Modify: `backend/tests/modules/test_feishu_document_contract.py`

- [ ] **Step 1: Add a narrow route for the aggregate lookup**
- [ ] **Step 2: Run the focused test file until green**
- [ ] **Step 3: Run the broader Feishu-related contract suite to guard regressions**
