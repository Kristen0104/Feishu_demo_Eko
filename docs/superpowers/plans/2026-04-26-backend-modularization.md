# Backend Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the backend into clear feature modules under `backend/app/modules/`, keep `backend/` as the only backend root, and annotate unfinished PRD gaps with explicit `TODO` comments in the owning files.

**Architecture:** The backend will be split by product domain rather than by technical layer alone. FastAPI routers stay thin, `services/` becomes orchestration glue, and feature logic moves into isolated modules such as `intent`, `feishu`, `rag`, `workspace`, `sync`, and `ppt`. The existing `ppt` implementation is already vendored and will remain the reference for a thin compatibility wrapper, while the rest of the backend is refactored to point at backend-local imports only.

**Tech Stack:** FastAPI, SQLAlchemy, Redis Pub/Sub, PostgreSQL/pgvector, Python 3.11, the vendored `ppt-master` codebase.

---

### Task 1: Define backend module boundaries

**Files:**
- Create: `backend/app/modules/intent/__init__.py`
- Create: `backend/app/modules/feishu/__init__.py`
- Create: `backend/app/modules/rag/__init__.py`
- Create: `backend/app/modules/workspace/__init__.py`
- Create: `backend/app/modules/sync/__init__.py`
- Modify: `backend/app/modules/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_modules_package_exists():
    assert Path("backend/app/modules/intent").exists()
    assert Path("backend/app/modules/feishu").exists()
    assert Path("backend/app/modules/rag").exists()
    assert Path("backend/app/modules/workspace").exists()
    assert Path("backend/app/modules/sync").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_backend_modules -v`
Expected: FAIL because the packages do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/modules/__init__.py
"""Application feature modules."""

# backend/app/modules/intent/__init__.py
"""Intent routing and classification."""

# backend/app/modules/feishu/__init__.py
"""Feishu integration module."""

# backend/app/modules/rag/__init__.py
"""Retrieval and knowledge base module."""

# backend/app/modules/workspace/__init__.py
"""Workspace and collaboration module."""

# backend/app/modules/sync/__init__.py
"""Realtime sync and broadcast module."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_backend_modules -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules tests/test_backend_modules.py docs/superpowers/plans/2026-04-26-backend-modularization.md
git commit -m "refactor: define backend module boundaries"
```

### Task 2: Move PPT feature logic behind backend-local imports

**Files:**
- Modify: `backend/app/services/ppt_service.py`
- Modify: `backend/app/services/ppt_template_service.py`
- Modify: `backend/app/api/ppt.py`
- Modify: `backend/app/api/ppt_templates.py`
- Modify: `backend/app/modules/ppt/generator.py`
- Modify: `backend/app/modules/ppt/template_import.py`
- Modify: `backend/app/modules/ppt/__init__.py`
- Modify: `backend/app/modules/ppt/README.md`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_ppt_services_import_from_backend_modules():
    text = Path("backend/app/services/ppt_service.py").read_text(encoding="utf-8")
    assert "from ..modules.ppt import AipptGenerator" in text

    text = Path("backend/app/services/ppt_template_service.py").read_text(encoding="utf-8")
    assert "from ..modules.ppt import TemplateImportService" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_backend_ppt_imports -v`
Expected: FAIL until the imports are normalized and old root-level references are removed.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/ppt_service.py
from ..modules.ppt import AipptGenerator

# backend/app/services/ppt_template_service.py
from ..modules.ppt import TemplateImportService

# backend/app/modules/ppt/README.md
Update the usage examples to point at `backend.app.modules.ppt` and `backend/vendor/ppt_master`.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_backend_ppt_imports -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ppt_service.py backend/app/services/ppt_template_service.py backend/app/modules/ppt docs/superpowers/plans/2026-04-26-backend-modularization.md
git commit -m "refactor: isolate ppt module behind backend imports"
```

### Task 3: Add PRD-linked TODO markers in core backend files

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/agent.py`
- Modify: `backend/app/api/canvas.py`
- Modify: `backend/app/api/rag.py`
- Modify: `backend/app/api/sessions.py`
- Modify: `backend/app/api/settings.py`
- Modify: `backend/app/api/webhook.py`
- Modify: `backend/app/services/intent_service.py`
- Modify: `backend/app/services/llm_service.py`
- Modify: `backend/app/services/feishu_service.py`
- Modify: `backend/app/core/state_machine.py`
- Modify: `backend/app/schemas/schemas.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_core_backend_files_have_prd_todos():
    files = [
        "backend/app/main.py",
        "backend/app/api/agent.py",
        "backend/app/api/canvas.py",
        "backend/app/api/rag.py",
        "backend/app/api/sessions.py",
        "backend/app/api/settings.py",
        "backend/app/api/webhook.py",
        "backend/app/services/intent_service.py",
        "backend/app/services/llm_service.py",
        "backend/app/services/feishu_service.py",
    ]
    joined = "\n".join(Path(path).read_text(encoding="utf-8") for path in files)
    assert "TODO(PRD-" in joined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_prd_todos -v`
Expected: FAIL until explicit PRD TODO comments are added.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/main.py
# TODO(PRD-2.3.2): split realtime sync and workspace orchestration into backend/app/modules/sync and backend/app/modules/workspace.
# TODO(PRD-4.2): move intent classification into backend/app/modules/intent.

# backend/app/services/intent_service.py
# TODO(PRD-2.1): extract intent routing rules into backend/app/modules/intent/classifier.py.

# backend/app/services/feishu_service.py
# TODO(PRD-2.2): isolate Feishu API clients and message-card handling under backend/app/modules/feishu.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_prd_todos -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/app/api/*.py backend/app/services/*.py backend/app/core/*.py backend/app/schemas/schemas.py docs/superpowers/plans/2026-04-26-backend-modularization.md
git commit -m "docs: add prd-linked backend todo markers"
```

### Task 4: Normalize backend-local PPT compatibility wrappers

**Files:**
- Modify: `aippt/__init__.py`
- Modify: `aippt/api_client.py`
- Modify: `aippt/config.py`
- Modify: `aippt/generator.py`
- Modify: `aippt/template_import.py`
- Modify: `aippt/template_matcher.py`
- Modify: `aippt/template_pack.py`
- Modify: `aippt/templates.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_aippt_only_reexports_backend_modules():
    text = Path("aippt/__init__.py").read_text(encoding="utf-8")
    assert "backend.app.modules.ppt" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_aippt_wrapper -v`
Expected: FAIL if any root-level implementation remains.

- [ ] **Step 3: Write minimal implementation**

```python
# aippt/__init__.py
from backend.app.modules.ppt import ...

# aippt/*.py
from backend.app.modules.ppt.<same_module> import *  # compatibility only
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_aippt_wrapper -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add aippt backend/app/modules/ppt docs/superpowers/plans/2026-04-26-backend-modularization.md
git commit -m "refactor: make aippt a thin compatibility layer"
```

### Task 5: Verify module graph and backend-only ownership

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/__init__.py`
- Modify: `backend/app/modules/ppt/README.md`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_backend_is_single_source_of_truth():
    assert Path("backend/app").exists()
    assert not Path("app").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_backend_layout -v`
Expected: FAIL unless backend-only ownership is documented and root-level backend claims are removed.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/__init__.py
"""Application service orchestration."""

# backend/app/modules/ppt/README.md
# TODO(PRD-2.4): add module ownership notes for multi-user collaboration.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_backend_layout -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/requirements.txt docs/superpowers/plans/2026-04-26-backend-modularization.md
git commit -m "chore: document backend single-root ownership"
```

