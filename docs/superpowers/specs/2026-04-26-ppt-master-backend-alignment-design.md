# PPT Master Backend Alignment Design

## Goal

Bring Eko's backend PPT generation flow into strict alignment with the vendored `ppt-master` workflow, so template-backed decks are generated through the same design-contract and executor model as the original project instead of through direct placeholder filling.

## Why This Change Is Needed

Our current backend path treats `ppt-master` templates as mostly-static SVGs that can be populated by replacing placeholders such as `{{TITLE}}` and `{{CONTENT_AREA}}`. That approach is fundamentally incompatible with the original project's execution model:

- In `ppt-master`, templates are visual anchors, not full content-page layouts.
- Content pages inherit the template's header/footer/brand language, but the main content area is re-designed by the Executor page by page.
- The Executor is constrained by `design_spec.md` and `spec_lock.md`, and it re-reads `spec_lock.md` before every page.
- The page-level `page_rhythm` contract (`anchor` / `dense` / `breathing`) is the mechanism that prevents every page from collapsing into the same generic layout pattern.

The visible symptoms in our current output match this mismatch exactly: large dashed content boxes, explanatory placeholder copy left on slides, sparse centered text, and layouts that look like incomplete scaffolds rather than finished pages.

## Source-of-Truth Workflow

The backend should align to this `ppt-master` pipeline:

1. Input prompt / chat history / uploaded context
2. Project creation
3. Template option selection
4. Strategist phase
5. `design_spec.md` generation
6. `spec_lock.md` generation
7. Executor phase
8. SVG quality checking
9. Post-processing
10. PPTX export

This is the workflow defined in:

- `backend/vendor/ppt_master/SKILL.md`
- `backend/vendor/ppt_master/references/strategist.md`
- `backend/vendor/ppt_master/references/executor-base.md`
- `backend/vendor/ppt_master/templates/layouts/README.md`

## Design Principles

### 1. Templates Are Anchors, Not Fill-In Forms

We should keep template inheritance for:

- Cover pages
- TOC pages
- Chapter pages
- Ending pages
- Content-page header/footer/brand scaffolding

We should not treat content-page SVG files as complete layouts whose central content can be satisfied by filling a single placeholder.

### 2. Content Pages Must Be Re-Laid Out By An Executor

For content pages, the backend must give the Executor:

- page title
- page brief
- page type
- page rhythm
- selected template
- deck color/typography/icon/image contract

The Executor then generates the full page SVG for that page's actual information density and narrative role.

### 3. `spec_lock.md` Must Become Runtime Truth

The original project is explicit that the Executor should re-read `spec_lock.md` before each page and only use values declared there. We should preserve this contract in backend form rather than replacing it with ad hoc in-memory style values.

At minimum the generated `spec_lock.md` must include:

- canvas
- colors
- typography
- icons
- images
- page_rhythm
- forbidden

### 4. The Backend May Wrap `ppt-master`, But Must Not Simplify Its Semantics Away

We can keep Eko-specific API endpoints and service interfaces, but they should wrap the original semantics instead of replacing them with a simpler placeholder engine.

That means:

- Eko endpoints may still accept prompt-like inputs.
- Eko may still expose `fast / hybrid / quality`.
- But the internal execution path for template-based decks must preserve Strategist -> Executor separation and page-level free design behavior.

## Proposed Backend Architecture

### A. Input Layer

Responsibility:

- Accept raw prompt, chat history, generation mode, and optional template hint.
- Normalize user input into a deck request.

Output:

- `PptDeckRequest`

Suggested fields:

- `raw_prompt`
- `chat_history`
- `generation_mode`
- `template_preference`
- `target_page_count`
- `source_context`

### B. Strategist Layer

Responsibility:

- Interpret the prompt and source context.
- Decide deck narrative, template usage, executor style, and page rhythm.
- Produce both a machine-readable contract and a human-readable design artifact.

Outputs:

- `design_spec.md`
- `spec_lock.md`
- `deck_outline.json` or equivalent backend structure

Minimum structure to generate:

- deck title and subtitle
- chosen template or free-design path
- deck-level color and typography contract
- icon library and inventory
- page list with page index, title, type, brief, and `page_rhythm`

Important rule:

The Strategist output must not be skipped even in `fast` mode. `Fast` may mean reduced depth, but it cannot mean skipping the design contract entirely.

### C. Template Resolver Layer

Responsibility:

- Resolve the chosen template folder from `layouts_index.json`.
- Copy or reference template assets into the project workspace exactly as the original project expects.

Behavior:

- `anchor` pages use the matching template SVG skeleton.
- `content` pages use template frame language only, not direct content fill.

### D. Executor Layer

Responsibility:

- Generate final per-page SVGs.
- Re-read `spec_lock.md` before each page.
- Apply `page_rhythm`.
- Respect template adherence rules from `executor-base.md`.

Rules:

- `anchor` pages: close adherence to template structure
- `dense` pages: charts, cards, grids, comparisons, multi-column layouts allowed
- `breathing` pages: avoid multi-card-grid default, use whitespace and hierarchy intentionally

Critical point:

This layer is where our current backend diverges most from `ppt-master`. Today we mostly skip this logic. That gap is the main thing to fix.

### E. Quality Gate

Responsibility:

- Run `svg_quality_checker.py` on `svg_output/`
- Fail or retry on structural SVG errors before post-processing

This should become a first-class backend step rather than an optional manual check.

### F. Post-Processing / Export Layer

Responsibility:

- `total_md_split.py`
- `finalize_svg.py`
- `svg_to_pptx.py -s final`

This part of the current backend is already directionally correct and can remain, but should run only after Executor output passes the quality gate.

## Mode Mapping

We should reinterpret Eko's three modes through the original workflow rather than letting them bypass it.

### `fast`

- Use Strategist Lite
- Generate compact `design_spec.md` and `spec_lock.md`
- Use template anchors when a template is selected
- Use Executor for content pages with simplified page briefs
- Run full quality gate and export

### `hybrid`

- Use richer Strategist output
- Use template anchors
- Let Executor generate all pages
- Allow selective AI refinement for designated hero pages or complex visualization pages

### `quality`

- Use full Strategist depth
- Use full Executor generation for all pages
- Permit more custom visualization and imagery decisions

The key point is that all three modes still pass through Strategist and Executor. They vary by depth, not by architecture.

## File and Module Direction

### Keep

- `backend/app/services/ppt_service.py`
- `backend/app/api/ppt.py`
- `backend/app/api/agent.py`
- `backend/app/modules/ppt/generator.py`
- vendored `backend/vendor/ppt_master/scripts/*`

### Reposition

- `backend/app/modules/ppt/template_pack.py`

This should stop being the primary page renderer for whole decks. It should become a helper for anchor-page inheritance and template frame extraction only.

### Add

- `backend/app/modules/ppt/strategist.py`
- `backend/app/modules/ppt/executor.py`
- `backend/app/modules/ppt/project_builder.py`
- `backend/app/modules/ppt/spec_lock.py`
- `backend/app/modules/ppt/models.py`

### Suggested Responsibilities

- `models.py`
  Typed deck request / outline / page brief / execution contract objects.

- `project_builder.py`
  Create workspace layout and write `design_spec.md`, `spec_lock.md`, and source artifacts.

- `strategist.py`
  Prompt-to-outline and prompt-to-design-contract generation.

- `executor.py`
  Page-by-page SVG generation with template adherence and `page_rhythm`.

- `spec_lock.py`
  Read/write/validate the execution contract.

## Backward Compatibility Plan

We should preserve current API shapes where possible, but change what they mean internally.

### `/api/v1/agent/ppt-test`

Can remain a testing route, but must become:

- prompt input
- strategist generation
- executor generation
- export

It should no longer synthesize a deck by hardcoded page placeholders.

### `/api/v1/ppt/generate`

This route can stay as the structured-input route for direct deck generation, but its semantics should be updated:

- structured input becomes a pre-baked outline
- backend still generates `design_spec.md` and `spec_lock.md`
- executor still owns content-page SVG creation

This keeps the API useful for testing and automation without bypassing the original architecture.

## What We Should Explicitly Stop Doing

1. Expanding placeholder substitution in `template_pack.py` as the main strategy
2. Treating `03_content.svg` as a finished slide whose center can be filled with bullet text
3. Skipping `design_spec.md` and `spec_lock.md`
4. Generating content pages without page-level rhythm or page briefs
5. Treating `fast` mode as permission to bypass the Strategist/Executor model

## Risks

### 1. Implementation Size

Aligning correctly to `ppt-master` is a larger change than incremental template fixes. This is acceptable because the smaller path keeps producing structurally wrong decks.

### 2. LLM Dependency Increase

Executor generation will increase dependence on model quality. This is expected in the original architecture. The mitigation is stronger contracts and quality gates, not reverting to placeholder fill.

### 3. Throughput

Page-by-page execution is slower than placeholder fill. This is also expected. The mitigation is using lighter Strategist and Executor prompts for `fast`, not removing those phases.

## Success Criteria

We should consider the alignment successful when:

- Content pages no longer look like partially filled template scaffolds
- Template-backed decks visually resemble native `ppt-master` output behavior
- `design_spec.md` and `spec_lock.md` are generated for template-based runs
- Content pages vary by `page_rhythm` instead of collapsing to one default layout
- Backend quality checks catch structural SVG issues before export
- Eko APIs still work, but now wrap the real `ppt-master` semantics

## Recommendation

Do not continue refining the current placeholder-based template path.

Instead, rebuild the backend PPT pipeline around a strict internal contract:

- Eko API as input shell
- Strategist as planning layer
- Template resolver as visual anchor layer
- Executor as page generator
- quality checker as gate
- `ppt-master` scripts as export tail

That is the smallest design that is both faithful to `ppt-master` and capable of producing decks that no longer feel structurally wrong.
