#!/usr/bin/env python3
"""
extract.py — CLI tool to extract dimensions and geometry from PDF technical drawings
and generate both a JSON data file and an OpenSCAD (.scad) parametric model.

Usage:
    python extract.py <input.pdf> [options]

Options:
    -o, --output DIR        Output directory (default: ./output)
    -e, --extrude FLOAT     Extrusion height in drawing units for 3D model
    --ai-only               Skip library parsing; go straight to Claude vision API
    --json-only             Only write the JSON file, skip .scad generation
    --api-key KEY           Anthropic API key (or set ANTHROPIC_API_KEY env var)
    -p, --page INT          PDF page index to process (default: 0)
    -v, --verbose           Print detailed progress

Examples:
    python extract.py bracket.pdf -e 10
    python extract.py scanned_drawing.pdf --ai-only -e 5 -o ./results
    python extract.py part.pdf --json-only
"""

from __future__ import annotations
import argparse
import json
import os
import sys


# ---------------------------------------------------------------------------
# Fallback detection threshold
# ---------------------------------------------------------------------------
MIN_DIMENSIONS = 2   # fewer than this triggers AI fallback
MIN_SHAPES = 1       # fewer than this (from library parse) triggers AI fallback


def main() -> None:
    args = _parse_args()

    pdf_path: str = args.input
    output_dir: str = args.output
    extrude_height: float | None = args.extrude
    ai_only: bool = args.ai_only
    json_only: bool = args.json_only
    api_key: str | None = args.api_key
    page_index: int = args.page
    verbose: bool = args.verbose

    if not os.path.isfile(pdf_path):
        _die(f"Input file not found: {pdf_path}")

    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    json_path = os.path.join(output_dir, f"{stem}.json")
    scad_path = os.path.join(output_dir, f"{stem}.scad")

    # ------------------------------------------------------------------
    # Stage 1 & 2: Library-based extraction
    # ------------------------------------------------------------------
    use_ai = ai_only
    drawing_data = None

    if not ai_only:
        _log(verbose, "Stage 1: Extracting vector paths from PDF…")
        try:
            from pdf_parser import extract_paths, extract_text_spans
            from dimension_parser import parse_dimensions_from_spans, infer_units
            from geometry_linker import link_dimensions
            from dataclasses import asdict

            shapes = extract_paths(pdf_path, page_index=page_index)
            spans = extract_text_spans(pdf_path, page_index=page_index)
            dimensions = parse_dimensions_from_spans(spans)
            units = infer_units(dimensions)

            _log(verbose, f"  → Found {len(shapes)} shape(s) and {len(dimensions)} dimension(s)")

            # Decide whether to fall back to AI
            if len(dimensions) < MIN_DIMENSIONS or len(shapes) < MIN_SHAPES:
                _log(
                    verbose,
                    f"  → Insufficient data (need ≥{MIN_DIMENSIONS} dims, ≥{MIN_SHAPES} shapes). "
                    "Falling back to Claude vision API.",
                )
                use_ai = True
            else:
                from data_model import DrawingData
                link_result = link_dimensions(dimensions, shapes)
                drawing_data = DrawingData(
                    source=os.path.basename(pdf_path),
                    units=units,
                    extraction_method="library",
                    dimensions=dimensions,
                    shapes=shapes,
                    extrude_height=extrude_height,
                    links=[asdict(l) for l in link_result.links],
                    orphans=[asdict(o) for o in link_result.orphans],
                )

        except ImportError as e:
            _die(
                f"PyMuPDF not installed. Run: pip install -r requirements.txt\n  ({e})"
            )

    # ------------------------------------------------------------------
    # Stage 2b: AI vision fallback
    # ------------------------------------------------------------------
    if use_ai:
        _log(verbose, "Stage 2b: Calling Claude vision API (claude-opus-4-6)…")
        try:
            from ai_extractor import extract_with_ai
            drawing_data = extract_with_ai(
                pdf_path,
                page_index=page_index,
                extrude_height=extrude_height,
                api_key=api_key,
            )
            _log(
                verbose,
                f"  → AI extracted {len(drawing_data.dimensions)} dimension(s) "
                f"and {len(drawing_data.shapes)} shape(s)",
            )
        except ImportError as e:
            _die(f"anthropic package not installed. Run: pip install -r requirements.txt\n  ({e})")
        except Exception as e:
            _die(f"AI extraction failed: {e}")

    if drawing_data is None:
        _die("No data could be extracted. Aborting.")

    # Override extrude_height if explicitly passed on CLI
    if extrude_height is not None:
        drawing_data.extrude_height = extrude_height

    # ------------------------------------------------------------------
    # Stage 3: Write JSON output
    # ------------------------------------------------------------------
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(drawing_data.to_json())
    print(f"JSON  → {json_path}")

    # ------------------------------------------------------------------
    # Stage 4: Write OpenSCAD output
    # ------------------------------------------------------------------
    if not json_only:
        from scad_generator import generate_scad
        generate_scad(drawing_data, scad_path)
        print(f".scad → {scad_path}")

    # Summary
    print(
        f"\nExtraction complete  |  method={drawing_data.extraction_method}"
        f"  |  units={drawing_data.units}"
        f"  |  {len(drawing_data.dimensions)} dimension(s)"
        f"  |  {len(drawing_data.shapes)} shape(s)"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract dimensions from a PDF technical drawing and generate OpenSCAD scripts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", metavar="INPUT.PDF", help="Path to the PDF technical drawing")
    parser.add_argument("-o", "--output", default="output", metavar="DIR",
                        help="Output directory (default: ./output)")
    parser.add_argument("-e", "--extrude", type=float, default=None, metavar="FLOAT",
                        help="Extrusion height for 3D model (drawing units)")
    parser.add_argument("--ai-only", action="store_true",
                        help="Skip library parsing; use Claude vision API directly")
    parser.add_argument("--json-only", action="store_true",
                        help="Only write JSON, skip .scad generation")
    parser.add_argument("--api-key", default=None, metavar="KEY",
                        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    parser.add_argument("-p", "--page", type=int, default=0, metavar="INT",
                        help="PDF page index to process (default: 0)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print detailed progress")
    return parser.parse_args()


def _log(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg)


def _die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
