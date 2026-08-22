"""Integration test: position-aware dimension parsing → geometry linking.

Generates a vector drawing with PyMuPDF (rect + circle + text callouts) and
asserts the full library path works end-to-end:
  * extract_text_spans returns per-line spans with bbox anchors
  * parse_dimensions_from_spans tags every dimension with a position
  * link_dimensions links typed dimensions (radius/diameter) to the circle
    and a generic mm dimension to the rectangle — with no orphans

Requires PyMuPDF (pymupdf) — silently skipped if not installed.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import pymupdf
except ImportError:  # pragma: no cover - depends on PyMuPDF being installed
    pymupdf = None

from pdf_parser import extract_paths, extract_text_spans  # noqa: E402
from dimension_parser import parse_dimensions_from_spans  # noqa: E402
from geometry_linker import link_dimensions  # noqa: E402


def _drawing(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    # Non-overlapping shapes so linking is unambiguous.
    page.draw_circle(pymupdf.Point(40, 100), 10, color=(0, 0, 0), width=1)   # r=10
    page.draw_rect(pymupdf.Rect(100, 80, 150, 110), color=(0, 0, 0), width=1)  # 50x30
    # Text callouts near their measured feature.
    page.insert_text(pymupdf.Point(32, 106), "Ø20", fontsize=8)   # diameter 20 → circle
    page.insert_text(pymupdf.Point(38, 96), "R10", fontsize=8)    # radius 10 → circle
    page.insert_text(pymupdf.Point(118, 74), "50 mm", fontsize=8)  # generic 50 → rect
    doc.save(str(path))
    doc.close()


def test_position_aware_parse_and_link() -> None:
    assert pymupdf is not None, "PyMuPDF required to run this test"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "drawing.pdf"
        _drawing(p)

        shapes = extract_paths(str(p))
        spans = extract_text_spans(str(p))
        dims = parse_dimensions_from_spans(spans)

        assert dims, "no dimensions parsed"
        assert all(dim.position is not None for dim in dims), (
            "every dimension must carry a text anchor position"
        )

        labels = {d.label for d in dims}
        assert "radius" in labels, f"radius callout not parsed: {labels}"
        assert "diameter" in labels, f"diameter callout not parsed: {labels}"
        assert "dimension" in labels, f"bare 50 mm not parsed: {labels}"

        result = link_dimensions(dims, shapes)
        assert result.links, "expected at least one linked dimension"
        assert not result.orphans, f"unexpected orphans: {result.orphans}"

        linked_types = {
            link.dimension.label: shapes[link.shape_index].type
            for link in result.links
        }
        assert linked_types["radius"] == "circle", linked_types
        assert linked_types["diameter"] == "circle", linked_types
        assert linked_types["dimension"] == "rectangle", linked_types
