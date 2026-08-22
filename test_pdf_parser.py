"""Regression tests for pdf_parser shape detection against real PyMuPDF output.

Generates a minimal vector drawing with PyMuPDF and asserts:
  * a rectangle path (single "re" item) is detected with correct width/height
  * a circle is detected with an ACCURATE radius (regression: was ~14% off
    because the code read the Bézier control point instead of the endpoint)

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

from pdf_parser import extract_paths  # noqa: E402


def _drawing(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    page.draw_rect(pymupdf.Rect(50, 50, 100, 80), color=(0, 0, 0), width=1)  # 50x30
    page.draw_circle(pymupdf.Point(65, 65), 5, color=(0, 0, 0), width=1)     # r=5
    doc.save(str(path))
    doc.close()


def test_extracts_rectangle_and_accurate_circle() -> None:
    assert pymupdf is not None, "PyMuPDF required to run this test"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "drawing.pdf"
        _drawing(p)
        shapes = extract_paths(str(p))

        types = {s.type for s in shapes}
        assert "rectangle" in types, f"rectangle not detected; got {types}"

        rect = next(s for s in shapes if s.type == "rectangle")
        assert abs(rect.width - 50.0) < 1.0
        assert abs(rect.height - 30.0) < 1.0

        circles = [s for s in shapes if s.type == "circle"]
        assert len(circles) == 1
        # regression: previously returned ~11.42 for a true r=5 circle
        assert abs(circles[0].radius - 5.0) < 0.05, (
            f"circle radius inaccurate: {circles[0].radius}"
        )
