"""Data model for extracted technical drawing data."""

from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Dimension:
    label: str          # e.g. "width", "diameter", "R"
    value: float        # numeric value
    unit: str           # "mm" or "inch"
    tolerance: str = "" # e.g. "±0.1" or ""
    position: Optional[list[float]] = None  # [x, y] of the text anchor, for geometry linking


@dataclass
class Shape:
    type: str                               # "polygon" | "circle" | "rectangle" | "arc"
    points: Optional[list[list[float]]] = None  # polygon [[x,y], ...]
    center: Optional[list[float]] = None    # circle/arc [x, y]
    radius: Optional[float] = None          # circle/arc
    x: Optional[float] = None              # rectangle origin
    y: Optional[float] = None
    width: Optional[float] = None          # rectangle
    height: Optional[float] = None         # rectangle


@dataclass
class DrawingData:
    source: str
    units: str                           # "mm" or "inch"
    extraction_method: str               # "library" or "ai"
    dimensions: list[Dimension] = field(default_factory=list)
    shapes: list[Shape] = field(default_factory=list)
    extrude_height: Optional[float] = None  # None = 2D only

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> "DrawingData":
        dimensions = [Dimension(**dim) for dim in d.get("dimensions", [])]
        shapes = [Shape(**s) for s in d.get("shapes", [])]
        return cls(
            source=d["source"],
            units=d.get("units", "mm"),
            extraction_method=d.get("extraction_method", "library"),
            dimensions=dimensions,
            shapes=shapes,
            extrude_height=d.get("extrude_height"),
        )
