"""Regex-based dimension and measurement parser for technical drawing text."""

from __future__ import annotations
import re
from data_model import Dimension

# ---------------------------------------------------------------------------
# Regex patterns ordered from most-specific to least-specific
# ---------------------------------------------------------------------------

# Diameter prefix: Ø or ø followed by a number
_RE_DIAMETER = re.compile(r'[Øø∅]\s*(\d+(?:\.\d+)?)', re.UNICODE)

# Radius prefix: R followed by a number (not part of a longer word)
_RE_RADIUS = re.compile(r'\bR\s*(\d+(?:\.\d+)?)\b')

# Tolerance: value ± tolerance  (also handles "+/-")
_RE_TOLERANCE = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:±|\+/-|\+/\-)\s*(\d+(?:\.\d+)?)\s*(mm|in(?:ch)?|")?',
    re.IGNORECASE,
)

# Plain millimetre value: number followed by mm (with optional space)
_RE_MM = re.compile(r'(\d+(?:\.\d+)?)\s*mm\b', re.IGNORECASE)

# Plain inch value: number followed by in / inch / "
_RE_INCH = re.compile(r'(\d+(?:\.\d+)?)\s*(?:in(?:ch)?|")\b', re.IGNORECASE)

# Bare number on its own line or after common label keywords
_RE_LABELED = re.compile(
    r'\b(width|height|depth|length|thickness|dia(?:meter)?|radius|bore|pitch)\b'
    r'[:\s=]+(\d+(?:\.\d+)?)\s*(mm|in(?:ch)?|")?',
    re.IGNORECASE,
)

# Dimension-line notation: two numbers separated by × or x (e.g. 50×30)
_RE_CROSS = re.compile(r'(\d+(?:\.\d+)?)\s*[×xX]\s*(\d+(?:\.\d+)?)\s*(mm)?', re.IGNORECASE)


def parse_dimensions(text: str, default_unit: str = "mm") -> list[Dimension]:
    """
    Parse all recognisable dimension values from raw drawing text.

    Returns a deduplicated list of Dimension objects, most-specific matches first.
    """
    dims: list[Dimension] = []
    seen_values: set[tuple[str, float]] = set()

    def add(label: str, value: float, unit: str, tolerance: str = "") -> None:
        key = (label, value)
        if key not in seen_values:
            seen_values.add(key)
            dims.append(Dimension(label=label, value=value, unit=unit, tolerance=tolerance))

    # 1. Diameter
    for m in _RE_DIAMETER.finditer(text):
        add("diameter", float(m.group(1)), default_unit)

    # 2. Radius
    for m in _RE_RADIUS.finditer(text):
        add("radius", float(m.group(1)), default_unit)

    # 3. Tolerance notation (captures the nominal value + tolerance string)
    for m in _RE_TOLERANCE.finditer(text):
        unit = _normalise_unit(m.group(3)) if m.group(3) else default_unit
        tol = f"±{m.group(2)}"
        add("dimension", float(m.group(1)), unit, tol)

    # 4. Millimetre values
    for m in _RE_MM.finditer(text):
        add("dimension", float(m.group(1)), "mm")

    # 5. Inch values
    for m in _RE_INCH.finditer(text):
        add("dimension", float(m.group(1)), "inch")

    # 6. Labeled keywords
    for m in _RE_LABELED.finditer(text):
        label = _normalise_label(m.group(1))
        unit = _normalise_unit(m.group(3)) if m.group(3) else default_unit
        add(label, float(m.group(2)), unit)

    # 7. Cross-notation (50×30 → width + height)
    for m in _RE_CROSS.finditer(text):
        unit = _normalise_unit(m.group(3)) if m.group(3) else default_unit
        add("width", float(m.group(1)), unit)
        add("height", float(m.group(2)), unit)

    return dims


def infer_units(dims: list[Dimension]) -> str:
    """Return 'mm' or 'inch' based on majority vote of parsed dimensions."""
    if not dims:
        return "mm"
    counts = {"mm": 0, "inch": 0}
    for d in dims:
        if d.unit in counts:
            counts[d.unit] += 1
    return max(counts, key=counts.get)


# --- Helpers ---

def _normalise_unit(raw: str) -> str:
    raw = raw.strip().lower()
    if raw in ('"', "in", "inch"):
        return "inch"
    return "mm"


def _normalise_label(raw: str) -> str:
    mapping = {
        "dia": "diameter",
        "diameter": "diameter",
        "radius": "radius",
        "width": "width",
        "height": "height",
        "depth": "depth",
        "length": "length",
        "thickness": "thickness",
        "bore": "bore",
        "pitch": "pitch",
    }
    return mapping.get(raw.lower(), raw.lower())
