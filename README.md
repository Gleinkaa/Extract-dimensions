# Extract Dimensions → OpenSCAD

Turn a PDF technical drawing into a parametric 3D model.

Point it at a mechanical drawing and it extracts the geometry (rectangles, circles,
polygons) and the labeled dimensions (mm, inch, Ø, R, tolerances), then writes:

| Output | Contents |
|--------|----------|
| `output/<name>.json` | structured data — shapes, dimensions, units, extrusion height |
| `output/<name>.scad` | OpenSCAD script — named parameters + `profile_2d()` + `linear_extrude()` |

Vector PDFs are parsed locally with PyMuPDF and cost nothing. Only when that comes up
short (scanned or raster drawings) does it fall back to the Claude vision API.

## Install

```bash
git clone https://github.com/Gleinkaa/Extract-dimensions.git
cd Extract-dimensions
pip install -r requirements.txt
```

Requires Python 3.10+ (the code uses `X | None` type syntax). The GUI needs `tkinter`,
which ships with most Python builds — on Debian/Ubuntu install it with
`sudo apt install python3-tk`.

The Anthropic API key is only needed for the AI fallback path:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

You can also pass it per-run with `--api-key`, or let the GUI prompt for it the first
time it is actually needed.

## Usage

### CLI

```bash
python extract.py drawing.pdf -e 10 -v
```

`-e 10` extrudes the profile to 10 units thick; omit it to get a 2D profile only.

| Flag | Meaning |
|------|---------|
| `-o, --output DIR` | output directory (default: `./output`) |
| `-e, --extrude FLOAT` | extrusion height in drawing units for the 3D model |
| `-p, --page INT` | PDF page index, 0-based (default: `0` = first page) |
| `--ai-only` | skip local parsing, go straight to the Claude vision API |
| `--json-only` | write only the JSON, skip `.scad` generation |
| `--api-key KEY` | Anthropic API key (overrides `ANTHROPIC_API_KEY`) |
| `-v, --verbose` | print each pipeline stage |

More examples:

```bash
python extract.py scanned_drawing.pdf --ai-only -e 5 -o ./results
python extract.py multipage.pdf -p 2 -e 12      # third page
python extract.py part.pdf --json-only
```

Then render the result:

```bash
openscad output/part.scad
```

### GUI

```bash
python app.py
```

A tkinter window with a file picker, output folder, extrude height, page number,
"Force AI vision" / "JSON only" checkboxes, a live log, and an "open output folder"
prompt when it finishes. Note that the GUI's page field is **1-based** ("first page = 1"),
unlike the CLI's `-p`.

To get a double-clickable desktop icon (Linux):

```bash
python install.py
```

That rewrites `extract-dimensions.desktop` with absolute paths for your checkout and
installs it to `~/Desktop` and `~/.local/share/applications`.

## How extraction works

```
PDF ──► pdf_parser (PyMuPDF vector paths + text)
          │
          ├─ ≥2 dimensions AND ≥1 shape ──► library path ($0)
          │
          └─ otherwise ──► rasterize page @200 DPI ──► Claude vision (~$0.01–0.05)
                                       │
                          DrawingData ─┴─► JSON + .scad
```

The thresholds live at the top of `extract.py` (`MIN_DIMENSIONS = 2`, `MIN_SHAPES = 1`).
`--ai-only` skips the decision entirely.

Dimension parsing is regex-based and recognises `Ø25`, `R5`, `50 mm`, `2.5"`,
`30 ±0.1`, `width: 40`, and `50×30` cross notation. Units are decided by majority vote
across everything parsed.

In the generated `.scad`, each extracted dimension becomes a named top-level variable, so
you can edit a value and re-render. Circles found alongside a larger outline are treated
as holes and subtracted via `difference()`.

## Key files

| File | Role |
|------|------|
| `extract.py` | CLI entry point; owns the library-vs-AI decision and writes both outputs |
| `pdf_parser.py` | PyMuPDF: vector paths → `Shape`s, page text, page → PNG for vision |
| `dimension_parser.py` | regex patterns for mm/inch/Ø/R/tolerance → `Dimension`s, unit inference |
| `ai_extractor.py` | Claude vision fallback — streams a request, parses the JSON reply |
| `data_model.py` | `DrawingData` / `Dimension` / `Shape` dataclasses and JSON serialization |
| `scad_generator.py` | renders `DrawingData` to a parametric `.scad` file |
| `app.py` | tkinter GUI; mirrors the CLI pipeline in a background thread |
| `install.py` | installs the desktop launcher and icon |
| `extract-dimensions.desktop`, `icon.png` | launcher assets (paths fixed up by `install.py`) |

## Claude API details

- Model: `claude-opus-4-6`, `thinking={"type": "adaptive"}`, `max_tokens=4096`
- Input: the PDF page rasterized at 200 DPI, sent as base64 PNG
- Output: bare JSON (no code fences) with `dimensions`, `shapes`, `units`, `extrude_height`
- Streamed via `.stream()` / `.get_final_message()` so long analyses don't time out

Cost: $0.00 for vector PDFs (never leaves your machine), roughly $0.01–0.05 per page when
the vision fallback runs.

## Notes and limitations

- Shape detection is heuristic: a path with ≥4 line segments is read as a rectangle, ≥4
  Bézier curves with low radius variance as a circle. Complex drawings with title blocks,
  hatching, or dimension leader lines will produce extra shapes you may want to prune from
  the JSON before generating the `.scad`.
- Coordinates come straight from PDF user space, with **y increasing downward**, so an
  extracted profile can appear mirrored relative to the drawing in OpenSCAD.
- Dimensions are extracted as values but are *not* linked to the geometry — the `.scad`
  parameters are declared for you to wire into the shapes by hand.
- The GUI saves the API key in plain text at `~/.config/extract-dimensions/config.json`.
  Prefer the `ANTHROPIC_API_KEY` env var if that matters to you.
- `requirements.txt` lists `pdfplumber`, but nothing currently imports it.

## License

No license file is present; all rights reserved by default.
