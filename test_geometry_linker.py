"""Tests for geometry_linker (dimension ↔ shape linking, Paper-1 core).

Synthetic shapes/dimensions exercise the linking rules:
  * typed dimensions link only to type-compatible shapes with matching values
  * generic dimensions link by proximity alone
  * a value that disagrees with the shape's measure is orphaned
  * a dimension with no position anchor is orphaned
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_model import Dimension, Shape  # noqa: E402
from geometry_linker import link_dimensions  # noqa: E402


def _circle(cx=10.0, cy=10.0, r=5.0) -> Shape:
    return Shape(type="circle", center=[cx, cy], radius=r)


def _rect(x=0.0, y=0.0, w=50.0, h=30.0) -> Shape:
    return Shape(type="rectangle", x=x, y=y, width=w, height=h)


def _dim(label: str, value: float, pos=None) -> Dimension:
    return Dimension(label=label, value=value, unit="mm", position=pos)


def test_typed_dimensions_link_to_matching_shape() -> None:
    shapes = [_circle(), _rect()]
    dims = [
        _dim("diameter", 10.0, [10.0, 8.0]),   # circle d=2r
        _dim("radius", 5.0, [12.0, 12.0]),     # circle r
        _dim("width", 50.0, [25.0, -2.0]),     # rectangle w
        _dim("height", 30.0, [-2.0, 15.0]),    # rectangle h
    ]
    res = link_dimensions(dims, shapes)
    assert len(res.links) == 4
    assert not res.orphans
    # diameter + radius land on the circle (index 0), width/height on rect (index 1)
    by_label = {l.dimension.label: l for l in res.links}
    assert by_label["diameter"].shape_index == 0
    assert by_label["radius"].shape_index == 0
    assert by_label["width"].shape_index == 1
    assert by_label["height"].shape_index == 1


def test_type_incompatible_dimension_is_orphaned() -> None:
    # "diameter" cannot measure a rectangle -> orphan even though it is close
    res = link_dimensions([_dim("diameter", 10.0, [25.0, 15.0])], [_rect()])
    assert not res.links
    assert len(res.orphans) == 1


def test_value_mismatch_is_orphaned() -> None:
    # radius 999 vs a r=5 circle -> size agreement fails -> orphan
    res = link_dimensions([_dim("radius", 999.0, [10.0, 10.0])], [_circle()])
    assert not res.links
    assert len(res.orphans) == 1


def test_generic_dimension_links_by_proximity() -> None:
    # generic "dimension" has no type signal -> nearest shape wins
    shapes = [_circle(), _rect()]
    res = link_dimensions([_dim("dimension", 25.0, [25.0, 15.0])], shapes)
    assert len(res.links) == 1
    assert res.links[0].shape_index == 1  # inside the rectangle


def test_missing_position_is_orphaned() -> None:
    res = link_dimensions([_dim("width", 50.0, None)], [_rect()])
    assert not res.links
    assert len(res.orphans) == 1
    assert "position" in res.orphans[0].reason
