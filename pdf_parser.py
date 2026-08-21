"""PDF vector path and text extraction using PyMuPDF."""

from __future__ import annotations
import math
from typing import Optional
import fitz  # PyMuPDF

from data_model import Shape


def extract_paths(pdf_path: str, page_index: int = 0) -> list[Shape]:
    """Extract vector shapes from a PDF page using PyMuPDF drawing paths."""
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    drawings = page.get_drawings()
    shapes: list[Shape] = []

    for path in drawings:
        rect = path.get("rect")
        items = path.get("items", [])

        # Detect filled rectangles / squares
        if rect and _is_rect_shape(items):
            r = fitz.Rect(rect)
            if r.width > 0.5 and r.height > 0.5:
                shapes.append(Shape(
                    type="rectangle",
                    x=round(r.x0, 4),
                    y=round(r.y0, 4),
                    width=round(r.width, 4),
                    height=round(r.height, 4),
                ))
            continue

        # Detect circles / arcs
        circle = _detect_circle(items)
        if circle:
            cx, cy, r = circle
            shapes.append(Shape(
                type="circle",
                center=[round(cx, 4), round(cy, 4)],
                radius=round(r, 4),
            ))
            continue

        # Collect polyline points → polygon
        points = _collect_polyline_points(items)
        if len(points) >= 3:
            shapes.append(Shape(
                type="polygon",
                points=[[round(p[0], 4), round(p[1], 4)] for p in points],
            ))

    doc.close()
    return shapes


def extract_raw_text(pdf_path: str, page_index: int = 0) -> str:
    """Extract all text from a PDF page."""
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    text = page.get_text("text")
    doc.close()
    return text


def extract_text_spans(pdf_path: str, page_index: int = 0) -> list[dict]:
    """Extract per-line text spans with bbox anchors from a PDF page.

    Returns a list of line dicts in reading order::

        {"text": str, "spans": [{"text": str, "x": float, "y": float}, ...]}

    where ``text`` is the line's spans joined with a single space and each
    span's (x, y) is the centre of its bbox. This is the position-aware input
    for ``dimension_parser.parse_dimensions_from_spans``.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    lines: list[dict] = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:  # text blocks only (0 = text, 1 = image)
            continue
        for line in block.get("lines", []):
            spans = []
            for span in line.get("spans", []):
                t = (span.get("text") or "").strip()
                if not t:
                    continue
                x0, y0, x1, y1 = span["bbox"]
                spans.append({"text": t, "x": (x0 + x1) / 2.0, "y": (y0 + y1) / 2.0})
            if spans:
                lines.append({"text": " ".join(s["text"] for s in spans), "spans": spans})
    doc.close()
    return lines


def pdf_page_to_png_bytes(pdf_path: str, page_index: int = 0, dpi: int = 200) -> bytes:
    """Rasterize a PDF page to PNG bytes for AI vision fallback."""
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


# --- Helpers ---

def _is_rect_shape(items: list) -> bool:
    """Return True if path items form a simple rectangle.

    PyMuPDF emits two rectangle forms: a stroked rectangle is four "l" (line)
    items, while a filled rectangle is a single "re" (rectangle) item. Handle
    both so a part outline is not silently dropped.
    """
    line_items = [i for i in items if i[0] == "l"]
    rect_items = [i for i in items if i[0] == "re"]
    return len(line_items) >= 4 or bool(rect_items)


def _detect_circle(items: list) -> Optional[tuple[float, float, float]]:
    """Return (cx, cy, radius) if items form a closed circular path, else None."""
    curve_items = [i for i in items if i[0] == "c"]
    if len(curve_items) < 4:
        return None
    # Collect the curve endpoints (not control points — see below).
    points = []
    for item in curve_items:
        # Bezier: item = ("c", start, ctrl1, ctrl2, end). Index 3 is ctrl2
        # (which sits ~14% outside the true radius); the endpoint is index 4.
        if len(item) >= 5:
            points.append(item[4])  # endpoint
    if not points:
        return None
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    radii = [math.hypot(p.x - cx, p.y - cy) for p in points]
    r = sum(radii) / len(radii)
    variance = sum((ri - r) ** 2 for ri in radii) / len(radii)
    if variance < r * 0.1:  # reasonably circular
        return cx, cy, r
    return None


def _collect_polyline_points(items: list) -> list[tuple[float, float]]:
    """Extract sequential point coordinates from a path's line/move items."""
    points: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for item in items:
        kind = item[0]
        if kind in ("m", "l") and len(item) >= 2:
            pt = item[1]
            coord = (pt.x, pt.y)
            if coord not in seen:
                seen.add(coord)
                points.append(coord)
        elif kind == "c" and len(item) >= 5:
            pt = item[4]  # endpoint (index 4), not the second control point
            coord = (pt.x, pt.y)
            if coord not in seen:
                seen.add(coord)
                points.append(coord)
    return points
