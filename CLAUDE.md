# Extract-dimensions — Project Memory

## What this project does
Extracts 2D geometry and labeled dimensions from PDF technical drawings and generates:
- `output/<name>.json` — structured data (shapes, dimensions, units)
- `output/<name>.scad` — parametric OpenSCAD model ready to render

## How to run
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

# CLI
python extract.py drawing.pdf -e 10 -v

# GUI (double-click equivalent)
python app.py
```

## Architecture: 5-module pipeline
| File | Role |
|------|------|
| `extract.py` | CLI entry point, hybrid decision logic |
| `pdf_parser.py` | PyMuPDF: vector paths → shapes, `get_text()` → raw text |
| `dimension_parser.py` | Regex: mm/inch/Ø/R/tolerance patterns → Dimension list |
| `ai_extractor.py` | Claude `claude-opus-4-6` vision API fallback (PNG base64) |
| `data_model.py` | `DrawingData` / `Dimension` / `Shape` dataclasses + JSON |
| `scad_generator.py` | Writes `.scad`: parameters + `profile_2d()` + `linear_extrude` |
| `app.py` | tkinter GUI: file picker, options, live log, opens output folder |

## Hybrid fallback rule
- Library path (free, $0): PyMuPDF finds ≥2 dims AND ≥1 shape → use library
- AI path (~$0.01–0.05): fewer than 2 dims or 0 shapes → call Claude vision API

## Claude API usage (ai_extractor.py)
- Model: `claude-opus-4-6`
- Thinking: `{"type": "adaptive"}` — do NOT use `budget_tokens`
- Input: PDF page rasterized at 200 DPI → PNG → base64
- Output: raw JSON (no fences) with `dimensions`, `shapes`, `units`, `extrude_height`
- Uses streaming (`.stream()` + `.get_final_message()`) to avoid timeouts

## Key CLI flags
```
-e / --extrude FLOAT    Extrusion height for 3D model (mm)
--ai-only               Skip library parsing, always call Claude
--json-only             Only write JSON, skip .scad
-p / --page INT         PDF page index (default: 0, i.e. page 1)
-v / --verbose          Show pipeline stages
```

## Git branch
`claude/extract-drawing-data-openscad-gwfCf`

## PR note
Creating PRs in this environment requires the user to visit:
`https://github.com/Gleinkaa/Extract-dimensions/compare/main...claude/extract-drawing-data-openscad-gwfCf`
The local git proxy handles push/pull auth opaquely — no GitHub token is accessible programmatically.

## Token cost summary
| Scenario | Cost |
|----------|------|
| Vector PDF (library path) | $0.00 |
| Raster/scanned PDF (AI fallback) | ~$0.01–0.05 |
| Force `--ai-only` | ~$0.01–0.05 |
