"""Attribute Adjacency Graph linker for technical-drawing dimensions.

Paper-1 ("Advanced Computer Vision Architectures for Dimension Extraction in
Technical Drawings") identifies the core failure of naive extraction as the
ORPHANED dimension: a value with no link back to the geometry it measures. This
module is the deterministic v1 of that linking step. It builds an Attribute
Adjacency Graph over dimensions + shapes, scores candidate edges by (type
affinity, size agreement, proximity), assigns each dimension to its best shape,
and explicitly reports orphans instead of silently emitting unlinked values.

It is deliberately dependency-free (pure Python). A trained GNN (the paper's
HGCNN over the same adjacency graph) is the intended replacement for the scoring
function once annotated data exists — the graph structure and orphan handling
stay the same, so this is not throwaway code, it is the pre-GNN baseline.

Usage:
    from geometry_linker import link_dimensions
    result = link_dimensions(dimensions, shapes)
    result.links     # [GeometryLink(dimension, shape_index, score, reason), ...]
    result.orphans   # [Orphan(dimension, reason), ...]
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from data_model import Dimension, Shape

_LINK_THRESHOLD = 0.4
_SIZE_MIN = 0.5  # typed dimensions must agree with the shape's measure within ~50%


@dataclass
class GeometryLink:
    dimension: Dimension
    shape_index: int
    score: float
    reason: str


@dataclass
class Orphan:
    dimension: Dimension
    reason: str


@dataclass
class LinkResult:
    links: list[GeometryLink] = None  # type: ignore[assignment]
    orphans: list[Orphan] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.links is None:
            self.links = []
        if self.orphans is None:
            self.orphans = []


# ---------------------------------------------------------------------------
# Shape reference geometry
# ---------------------------------------------------------------------------

def _shape_bbox(shape: Shape) -> Optional[tuple[float, float, float, float]]:
    """Return (minx, miny, maxx, maxy) for the shape, or None."""
    if shape.type == "rectangle" and shape.x is not None:
        return (shape.x, shape.y, shape.x + shape.width, shape.y + shape.height)
    if shape.type in ("circle", "arc") and shape.center and shape.radius:
        cx, cy = shape.center
        r = shape.radius
        return (cx - r, cy - r, cx + r, cy + r)
    if shape.type == "polygon" and shape.points:
        xs = [p[0] for p in shape.points]
        ys = [p[1] for p in shape.points]
        return (min(xs), min(ys), max(xs), max(ys))
    return None


def _shape_measures(shape: Shape) -> dict[str, float]:
    """Named measures a dimension can target, e.g. {"diameter": 10, "radius": 5}."""
    if shape.type == "circle" and shape.radius:
        r = shape.radius
        return {"diameter": 2 * r, "radius": r}
    if shape.type == "arc" and shape.radius:
        return {"radius": shape.radius}
    if shape.type == "rectangle" and shape.width is not None:
        return {"width": shape.width, "height": shape.height or 0.0}
    if shape.type == "polygon":
        bbox = _shape_bbox(shape)
        if bbox:
            return {"width": bbox[2] - bbox[0], "height": bbox[3] - bbox[1]}
    return {}


def _bbox_diagonal(bbox: tuple[float, float, float, float]) -> float:
    return math.hypot(bbox[2] - bbox[0], bbox[3] - bbox[1])


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _label_targets(label: str) -> list[str]:
    """Map a dimension label to the shape measure(s) it can target.

    An empty list means the label is generic (no type signal) — it links by
    proximity alone. Length/depth/thickness/bore/pitch are intentionally generic
    in v1: without GD&T context they are ambiguous about which measure they hit.
    """
    mapping = {
        "diameter": ["diameter"],
        "radius": ["radius"],
        "width": ["width"],
        "height": ["height"],
    }
    return mapping.get((label or "").lower(), [])


def _size_match(value: float, measure: float) -> float:
    """0..1 relative agreement between a value and a shape measure."""
    if measure <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(value - measure) / measure)


def _point_in_bbox(p: list[float], bbox: tuple[float, float, float, float]) -> bool:
    x, y = p
    minx, miny, maxx, maxy = bbox
    return minx <= x <= maxx and miny <= y <= maxy


def _bbox_distance(p: list[float], bbox: tuple[float, float, float, float]) -> float:
    """Euclidean distance from a point to a bbox (0 if inside)."""
    if _point_in_bbox(p, bbox):
        return 0.0
    minx, miny, maxx, maxy = bbox
    dx = max(minx - p[0], 0.0, p[0] - maxx)
    dy = max(miny - p[1], 0.0, p[1] - maxy)
    return math.hypot(dx, dy)


def _proximity(position: list[float], shape: Shape) -> float:
    """0..1 spatial closeness of the dimension anchor to the shape."""
    bbox = _shape_bbox(shape)
    if bbox is None:
        return 0.0
    dist = _bbox_distance(position, bbox)
    scale = max(_bbox_diagonal(bbox), 1e-6)
    return max(0.0, 1.0 - dist / scale)


def _score(dim: Dimension, shape: Shape) -> Optional[float]:
    """Combined score for a (dimension, shape) edge, or None if incompatible."""
    if dim.position is None:
        return None
    targets = _label_targets(dim.label)
    measures = _shape_measures(shape)
    if targets:
        matched = {t: measures[t] for t in targets if t in measures}
        if not matched:
            return None  # type-incompatible: this label cannot measure this shape
        size = max(_size_match(dim.value, v) for v in matched.values())
        if size < _SIZE_MIN:
            return None  # value disagrees with the shape's measure
        return 0.5 * size + 0.5 * _proximity(dim.position, shape)
    # Generic label: no type signal, proximity alone decides.
    return _proximity(dim.position, shape)


# ---------------------------------------------------------------------------
# Linking
# ---------------------------------------------------------------------------

def link_dimensions(dimensions: list[Dimension], shapes: list[Shape]) -> LinkResult:
    """Link each dimension to its best shape, reporting the rest as orphans."""
    result = LinkResult()
    for dim in dimensions:
        best: Optional[tuple[int, float, str]] = None
        for idx, shape in enumerate(shapes):
            score = _score(dim, shape)
            if score is None:
                continue
            if best is None or score > best[1]:
                reason = f"{dim.label} {dim.value}{dim.unit} ↔ {shape.type}"
                best = (idx, score, reason)
        if best is None:
            result.orphans.append(Orphan(dim, _orphan_reason(dim)))
        elif best[1] < _LINK_THRESHOLD:
            result.orphans.append(Orphan(dim, f"no confident shape (score {best[1]:.2f})"))
        else:
            result.links.append(GeometryLink(dim, best[0], round(best[1], 3), best[2]))
    return result


def _orphan_reason(dim: Dimension) -> str:
    if dim.position is None:
        return "no position anchor (text position not extracted)"
    return "no type-compatible shape with a matching measure"
