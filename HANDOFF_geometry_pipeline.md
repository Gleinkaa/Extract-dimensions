# Geometry Pipeline — Handoff

> **To resume:** open a fresh session and say
> *"continue the geometry pipeline from HANDOFF_geometry_pipeline.md — start with the dimension_parser fixes"*
> This file has everything needed to pick up the work.

## Branch & repo state

- **Branch:** `geometry-linking` (off `main`)
- **Working tree:** clean except untracked `__pycache__/`
- **Latest commits (newest first):**
  1. `3e65cbb` Fix rectangle detection + accurate circle radius (real-world test bugs)
  2. `80826f0` Add geometry linker: link dimensions to shapes and flag orphans
  3. `e5971f3` docs: add/update README.md
  4. `655c4d0` Add desktop icon + on-demand info dialogs
  5. `a147f25` Add CLAUDE.md project memory
  6. `d2b4d58` Add tkinter GUI launcher (app.py)
  7. `6fd167e` Add PDF-to-OpenSCAD extraction pipeline

## Pipeline architecture (5 modules + linker)

| File | Role | Status |
|------|------|--------|
| `extract.py` | CLI entry point, hybrid decision logic | ✅ but **does not call geometry_linker yet** |
| `pdf_parser.py` | PyMuPDF: vector paths → shapes, `get_text()` → raw text | ✅ rectangle + circle-radius bugs fixed in `3e65cbb` |
| `dimension_parser.py` | Regex: mm/inch/Ø/R/tolerance patterns → `Dimension` list | ❌ **THE WORK — see below** |
| `geometry_linker.py` | Attribute Adjacency Graph: link dims↔shapes, flag orphans | ✅ built + synthetic tests, **not wired into pipeline** |
| `ai_extractor.py` | Claude `claude-opus-4-6` vision API fallback | ✅ unchanged |
| `data_model.py` | `DrawingData` / `Dimension` / `Shape` dataclasses + JSON | ✅ (may need links/orphans fields — see step 2) |
| `scad_generator.py` | Writes `.scad` | ✅ unchanged |
| `app.py` | tkinter GUI | ✅ unchanged |

Tests:
- `test_geometry_linker.py` — 5 synthetic tests (typed linking, type-incompat orphan, value-mismatch orphan, proximity linking, missing-position orphan). **Needs pytest.**
- `test_pdf_parser.py` — 1 regression test (rectangle dims + accurate circle radius r=5). **Needs PyMuPDF + pytest.**

## ⚠️ Environment setup (DO THIS FIRST)

The project deps are **not installed** in a fresh shell. Run:

```bash
cd /home/nik/dev/Extract-dimensions
pip install -r requirements.txt
pip install pytest           # NOT in requirements.txt — needed to run the tests
```

`requirements.txt` currently lists: `anthropic>=0.40.0`, `PyMuPDF>=1.24.0`, `pdfplumber>=0.11.0`.
**Add `pytest` to requirements.txt** (or a `requirements-dev.txt`) as part of this work — the tests can't run without it.

Verify the env works before changing code:
```bash
python3 -m pytest test_geometry_linker.py test_pdf_parser.py -v
```

## The work: dimension_parser fixes

> **STATUS: DONE.** Fixes 1–4 are implemented and committed (`7 passed`).
> Library path now parses positions, links dimensions↔shapes, and emits
> `links`/`orphans` in JSON. Non-blocking follow-ups: AI-path positions/bboxes,
> and the PyMuPDF 1.28 `import fitz` → `import pymupdf` deprecation warning.

### The core problem

`geometry_linker.link_dimensions(dimensions, shapes)` requires **`Dimension.position`** (an `[x, y]` text anchor) to score edges. Look at `geometry_linker.py:155`:

```python
def _score(dim: Dimension, shape: Shape) -> Optional[float]:
    if dim.position is None:
        return None   # ← every dimension with no position is orphaned
```

But `dimension_parser.parse_dimensions(text: str)` (see `dimension_parser.py:40`) takes **only raw text** and never sets `position`. `extract.py:72` calls it with `raw_text` from `extract_raw_text()` (plain string). So on any real PDF, **every dimension becomes an orphan** with reason `"no position anchor (text position not extracted)"`. The linker is dead code until this is fixed.

### Fix 1 — Position-aware dimension parsing (the main fix)

Refactor `dimension_parser.py` so dimensions carry their text coordinates.

**Approach (recommended):** add a new function that takes PyMuPDF span/word data (with bboxes) instead of a flat string, runs the same regexes per-span, and sets `Dimension.position` to the span bbox center `[cx, cy]`.

- PyMuPDF gives coordinates via `page.get_text("dict")` → `block["lines"][i]["spans"][j]` where each span has `"text"` and `"bbox" = (x0, y0, x1, y1)`. Use the bbox center: `[(x0+x1)/2, (y0+y1)/2]`.
- Keep `parse_dimensions(text: str, ...)` as a position-less fallback (AI path / tests still use it), but add e.g. `parse_dimensions_from_spans(spans: list[dict], default_unit="mm") -> list[Dimension]` where each span dict is `{"text": str, "bbox": (x0,y0,x1,y1)}`.
- Reuse the same compiled regexes (`_RE_DIAMETER`, `_RE_RADIUS`, etc.) — just run `finditer` against each span's text and tag the resulting `Dimension` with that span's bbox center.
- Dedup key currently is `(label, value)` — with positions, two identical values at different locations are genuinely different dimension callouts. Consider widening the dedup key to `(label, value, round(x), round(y))` so positional duplicates aren't collapsed.

**Wire it in `extract.py`:** replace
```python
raw_text = extract_raw_text(pdf_path, page_index=page_index)
dimensions = parse_dimensions(raw_text)
```
with a position-aware extraction that pulls spans from `page.get_text("dict")`. Either add an `extract_text_spans(pdf_path, page_index) -> list[dict]` to `pdf_parser.py` (sibling to `extract_raw_text`), or have `dimension_parser` import fitz directly (less clean — keep fitz in `pdf_parser`).

### Fix 2 — Wire geometry_linker into the pipeline

`extract.py` never imports `geometry_linker`. After Fix 1, call it in the library path (around `extract.py:86`, after building `dimensions` and `shapes`):

```python
from geometry_linker import link_dimensions
link_result = link_dimensions(dimensions, shapes)
# attach to drawing_data
```

Decision needed: how to surface links/orphans in output.
- **Option A (minimal):** add `links: list[dict]` and `orphans: list[dict]` fields to `DrawingData` in `data_model.py`, populate from `LinkResult`. JSON output then carries the linking.
- **Option B:** log orphan count in verbose mode only, keep JSON shape as-is. (Loses info — not recommended.)
Prefer Option A; update `DrawingData.to_json` / `from_dict` accordingly (dataclass + `asdict` handles it automatically once fields exist).

`scad_generator.py` should ignore links/orphans (it already iterates `dimensions`/`shapes`).

### Fix 3 — pytest as a declared dev dependency

Add `pytest` to `requirements.txt` or create `requirements-dev.txt` with `pytest`. The two test files have no `if __name__ == "__main__"` runner, so they **require pytest** — running `python3 test_geometry_linker.py` just defines functions and exits 0 without running assertions.

### Fix 4 (optional, good hygiene) — Add a position-aware test

`test_geometry_linker.py` already passes `position=[...]` in its `_dim` helper, so it tests the linker in isolation. Add one test that exercises the new position-aware parser path end-to-end against the same synthetic PDF used in `test_pdf_parser.py` (draw a rect + a circle + text labels with known coordinates, assert the dimensions get correct positions and link to the right shapes). This is the integration test that proves Fix 1 + Fix 2 work together.

## Hybrid fallback rule (unchanged, for reference)

- Library path (free): PyMuPDF finds ≥2 dims AND ≥1 shape → use library
- AI path (~$0.01–0.05): fewer than 2 dims or 0 shapes → Claude vision API
- Constants: `MIN_DIMENSIONS = 2`, `MIN_SHAPES = 1` (`extract.py:34-35`)

## Done definition for this round

- [x] `pip install` works and `pytest` is declared (`requirements-dev.txt`)
- [x] `python3 -m pytest test_geometry_linker.py test_pdf_parser.py -v` passes
- [x] `dimension_parser` produces `Dimension` objects with `position` set from real PDF text spans
- [x] `extract.py` calls `geometry_linker.link_dimensions` and links/orphans appear in the output JSON
- [x] At least one integration test covers position-aware parse → link on a synthetic PDF
- [x] Commit on `geometry-linking` branch with a clear message

## Key files to read first when resuming

1. `dimension_parser.py` (125 lines) — the file being changed
2. `geometry_linker.py` (199 lines) — the consumer; note `_score` at line 153 and `_orphan_reason` at 196
3. `extract.py:64-94` — the library-path block to modify
4. `data_model.py` — `Dimension.position` field already exists (line 15); `DrawingData` needs links/orphans fields
5. `test_geometry_linker.py` — pattern to follow for new tests