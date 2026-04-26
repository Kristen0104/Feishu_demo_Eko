# Source-Faithful Template Pack Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert reference PPTX decks into reusable template packs built from the deck's own exported SVG pages, so the generator can reuse the source's real visual language instead of mapping it onto official template families.

**Architecture:** Keep the existing `pptx_template_import.py` export path, including the macOS Keynote bridge. Change `TemplateImportService` so it consumes the exported SVG workspace from that script, selects representative source pages for template slots, and writes a template pack that `TemplatePack` can render directly. Preserve `template_pack.json` and API shape for compatibility, but make the pack content source-derived rather than copied from `skills/ppt-master/templates/layouts`.

**Tech Stack:** Python 3.11, `python-pptx`, `fitz`/PyMuPDF, FastAPI service layer, existing SVG validation helpers.

---

### Task 1: Make the importer pack source SVGs instead of copying official layouts

**Files:**
- Modify: `aippt/template_import.py`
- Test: `tests/test_template_import.py`

- [ ] **Step 1: Write the failing test**

```python
def test_import_sources_copies_source_svg_slots_and_assets():
    ...
    self.assertTrue((pack_dir / "svg" / "01_cover.svg").exists())
    self.assertTrue((pack_dir / "assets").exists())
    self.assertTrue((pack_dir / "template_pack.json").exists())
    self.assertNotIn("academic_defense", pack_dir.as_posix())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_template_import.TemplateImportServiceTests.test_import_sources_copies_source_svg_slots_and_assets -v`
Expected: FAIL because the importer still copies official template layouts.

- [ ] **Step 3: Write minimal implementation**

Implement `TemplateImportService._import_one()` so it reads the exported source SVG workspace, selects representative slide SVGs for `cover`, `toc`, `chapter`, `content`, and `ending`, copies those SVGs into `pack_dir/svg/`, and copies the source `assets/` directory into `pack_dir/assets/`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_template_import.TemplateImportServiceTests.test_import_sources_copies_source_svg_slots_and_assets -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add aippt/template_import.py tests/test_template_import.py
git commit -m "feat: build template packs from source svg exports"
```

### Task 2: Let template packs resolve files from the new source-derived pack layout

**Files:**
- Modify: `aippt/template_pack.py`
- Test: `tests/test_template_pack.py`

- [ ] **Step 1: Write the failing test**

```python
def test_template_pack_reads_svg_subdirectory_layout_files():
    ...
    self.assertTrue(pack.render({"layout": "cover", "title": "Demo"}).startswith("<svg"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_template_pack.TemplatePackTests.test_template_pack_reads_svg_subdirectory_layout_files -v`
Expected: FAIL because `TemplatePack` only checks the pack root.

- [ ] **Step 3: Write minimal implementation**

Teach `TemplatePack` to look for each layout file in the pack root first, then in `svg/`, so both legacy packs and the new source-derived packs render correctly.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_template_pack.TemplatePackTests.test_template_pack_reads_svg_subdirectory_layout_files -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add aippt/template_pack.py tests/test_template_pack.py
git commit -m "feat: support svg subdirectory template packs"
```

### Task 3: Refresh service-level tests and pack metadata expectations

**Files:**
- Modify: `backend/app/services/ppt_template_service.py` if needed
- Modify: `tests/test_ppt_template_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_list_packs_keeps_source_pack_metadata():
    ...
    self.assertEqual("/tmp/ref.pptx", packs[0]["source_pptx"])
    self.assertEqual("source_svg", packs[0]["base_template"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_ppt_template_service.PptTemplateServiceTests.test_list_packs_keeps_source_pack_metadata -v`
Expected: FAIL until the importer writes source-pack metadata.

- [ ] **Step 3: Write minimal implementation**

Keep the list/import API stable, but have new packs record a source-derived `base_template` label and source SVG metadata that matches the actual pack layout.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ppt_template_service.py tests/test_ppt_template_service.py
git commit -m "test: cover source-derived template pack metadata"
```
