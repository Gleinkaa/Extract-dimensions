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
    Positions are NOT populated — use :func:`parse_dimensions_from_spans` when
    the text anchor coordinates are needed for geometry linking.
    """
    dims: list[Dimension] = []
    seen: set = set()
    for label, value, unit, tol, _start, _end in _iter_dimension_matches(text, default_unit):
        _append_dim(dims, seen, label, value, unit, tol, position=None)
    return dims


def parse_dimensions_from_spans(lines: list[dict], default_unit: str = "mm") -> list[Dimension]:
    """
    Parse dimensions from per-line span data, tagging each with its anchor.

    ``lines`` is the output of ``pdf_parser.extract_text_spans``: a list of
    dicts ``{"text": <joined line text>, "spans": [{"text", "x", "y"}, ...]}``.
    Each matched dimension's ``position`` is the average of the bbox centres of
    the spans its match overlaps.
    """
    dims: list[Dimension] = []
    seen: set = set()

    for line in lines:
        text = line.get("text", "")
        spans = line.get("spans", [])
        if not text or not spans:
            continue

        # Map each span to its [start, end) character range in the joined text.
        ranges: list[tuple[int, int, float, float]] = []
        pos = 0
        for s in spans:
            st, en = pos, pos + len(s["text"])
            ranges.append((st, en, s["x"], s["y"]))
            pos = en + 1  # single space separator between spans

        def anchor(start: int, end: int) -> list[float]:
            xs = [x for st, en, x, _y in ranges if en > start and st < end]
            ys = [y for st, en, _x, y in ranges if en > start and st < end]
            if not xs:
                return [spans[0]["x"], spans[0]["y"]]
            return [sum(xs) / len(xs), sum(ys) / len(ys)]

        for label, value, unit, tol, start, end in _iter_dimension_matches(text, default_unit):
            _append_dim(dims, seen, label, value, unit, tol, anchor(start, end))

    return dims


def _iter_dimension_matches(text: str, default_unit: str):
    """Yield (label, value, unit, tolerance, start, end) for every regex match."""
    # 1. Diameter
    for m in _RE_DIAMETER.finditer(text):
        yield "diameter", float(m.group(1)), default_unit, "", m.start(), m.end()

    # 2. Radius
    for m in _RE_RADIUS.finditer(text):
        yield "radius", float(m.group(1)), default_unit, "", m.start(), m.end()

    # 3. Tolerance notation (captures the nominal value + tolerance string)
    for m in _RE_TOLERANCE.finditer(text):
        unit = _normalise_unit(m.group(3)) if m.group(3) else default_unit
        tol = f"±{m.group(2)}"
        yield "dimension", float(m.group(1)), unit, tol, m.start(), m.end()

    # 4. Millimetre values
    for m in _RE_MM.finditer(text):
        yield "dimension", float(m.group(1)), "mm", "", m.start(), m.end()

    # 5. Inch values
    for m in _RE_INCH.finditer(text):
        yield "dimension", float(m.group(1)), "inch", "", m.start(), m.end()

    # 6. Labeled keywords
    for m in _RE_LABELED.finditer(text):
        label = _normalise_label(m.group(1))
        unit = _normalise_unit(m.group(3)) if m.group(3) else default_unit
        yield label, float(m.group(2)), unit, "", m.start(), m.end()

    # 7. Cross-notation (50×30 → width + height)
    for m in _RE_CROSS.finditer(text):
        unit = _normalise_unit(m.group(3)) if m.group(3) else default_unit
        yield "width", float(m.group(1)), unit, "", m.start(), m.end()
        yield "height", float(m.group(2)), unit, "", m.start(), m.end()


def _dedup_key(label: str, value: float, position: list[float] | None):
    """Dedup key: positional callouts at different anchors are distinct."""
    if position is None:
        return (label, value)
    return (label, round(value, 4), round(position[0], 1), round(position[1], 1))


def _append_dim(dims: list[Dimension], seen: set, label: str, value: float,
                unit: str, tolerance: str, position: list[float] | None) -> None:
    key = _dedup_key(label, value, position)
    if key not in seen:
        seen.add(key)
        dims.append(Dimension(
            label=label, value=value, unit=unit, tolerance=tolerance, position=position,
        ))


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
