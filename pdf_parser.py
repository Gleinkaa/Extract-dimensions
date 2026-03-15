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
    """Return True if path items form a simple rectangle (4 lines, right angles)."""
    line_items = [i for i in items if i[0] == "l"]
    return len(line_items) >= 4


def _detect_circle(items: list) -> Optional[tuple[float, float, float]]:
    """Return (cx, cy, radius) if items form a closed circular path, else None."""
    curve_items = [i for i in items if i[0] == "c"]
    if len(curve_items) < 4:
        return None
    # Collect all control point endpoints
    points = []
    for item in curve_items:
        # Bezier: item = ("c", p1, p2, p3)
        if len(item) >= 4:
            points.append(item[3])  # endpoint
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
        elif kind == "c" and len(item) >= 4:
            pt = item[3]
            coord = (pt.x, pt.y)
            if coord not in seen:
                seen.add(coord)
                points.append(coord)
    return points
