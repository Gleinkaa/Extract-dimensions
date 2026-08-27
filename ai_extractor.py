"""Claude vision API fallback for extracting dimensions and shapes from PDF drawings."""

from __future__ import annotations
import base64
import json
import os

import anthropic

from data_model import Dimension, DrawingData, Shape
from pdf_parser import pdf_page_to_png_bytes

_SYSTEM_PROMPT = """\
You are a technical drawing analyst specializing in mechanical and engineering drawings.
Analyze the provided drawing image and extract all geometric and dimensional data.
Respond ONLY with a valid JSON object — no markdown fences, no prose."""

_USER_PROMPT = """\
Extract all data from this technical drawing and return a JSON object with this exact schema:

{
  "units": "mm",
  "dimensions": [
    {"label": "<name>", "value": <float>, "unit": "mm", "tolerance": "<±X or empty string>"}
  ],
  "shapes": [
    <one of the shape types below>
  ],
  "extrude_height": <float or null>
}

Shape types (include only the fields relevant to each type):
  Rectangle: {"type": "rectangle", "x": <float>, "y": <float>, "width": <float>, "height": <float>}
  Circle:    {"type": "circle", "center": [<float>, <float>], "radius": <float>}
  Polygon:   {"type": "polygon", "points": [[<float>, <float>], ...]}
  Arc:       {"type": "arc", "center": [<float>, <float>], "radius": <float>}

Rules:
- Use coordinate values relative to the drawing's own unit system (mm or inch).
- If the drawing has a title block or notes, infer units from there; otherwise default to mm.
- For extrude_height: if a depth/thickness dimension is explicitly shown, use it; otherwise null.
- Deduplicate dimensions — list each unique measurement once.
- Dimension labels should be descriptive: "width", "height", "diameter", "radius", "pitch", etc.
- If you cannot determine a coordinate precisely, use your best estimate from the drawing scale.
"""


def extract_with_ai(
    pdf_path: str,
    page_index: int = 0,
    extrude_height: float | None = None,
    api_key: str | None = None,
) -> DrawingData:
    """
    Rasterize a PDF page and send it to Claude vision to extract drawing data.

    Parameters
    ----------
    pdf_path:       Path to the PDF file.
    page_index:     Which page to process (0-based).
    extrude_height: Override extrusion height; if None, Claude's answer is used.
    api_key:        Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    oauth = os.environ.get("ANTHROPIC_OAUTH_TOKEN")
    if key:
        client = anthropic.Anthropic(api_key=key)
    elif oauth:
        # OAuth token route (sk-ant-oat01-...): used when no API key is set.
        client = anthropic.Anthropic(auth_token=oauth)
    else:
        raise ValueError("No Anthropic credentials: set ANTHROPIC_API_KEY or ANTHROPIC_OAUTH_TOKEN")

    # Rasterize the page to PNG
    png_bytes = pdf_page_to_png_bytes(pdf_path, page_index=page_index, dpi=200)
    image_b64 = base64.standard_b64encode(png_bytes).decode("utf-8")

    # Call Claude with vision + adaptive thinking for best accuracy
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": _USER_PROMPT},
                ],
            }
        ],
    ) as stream:
        response = stream.get_final_message()

    # Extract text block (may be preceded by a thinking block)
    raw_json = ""
    for block in response.content:
        if block.type == "text":
            raw_json = block.text.strip()
            break

    if not raw_json:
        raise ValueError("Claude returned no text content. Check the drawing image.")

    data = json.loads(raw_json)

    dimensions = [
        Dimension(
            label=d.get("label", "dimension"),
            value=float(d["value"]),
            unit=d.get("unit", data.get("units", "mm")),
            tolerance=d.get("tolerance", ""),
        )
        for d in data.get("dimensions", [])
    ]

    shapes = [_parse_shape(s) for s in data.get("shapes", [])]

    resolved_extrude = extrude_height if extrude_height is not None else data.get("extrude_height")

    import os as _os
    source_name = _os.path.basename(pdf_path)

    return DrawingData(
        source=source_name,
        units=data.get("units", "mm"),
        extraction_method="ai",
        dimensions=dimensions,
        shapes=shapes,
        extrude_height=resolved_extrude,
    )


def _parse_shape(s: dict) -> Shape:
    shape_type = s.get("type", "polygon")
    if shape_type == "rectangle":
        return Shape(
            type="rectangle",
            x=s.get("x"),
            y=s.get("y"),
            width=s.get("width"),
            height=s.get("height"),
        )
    if shape_type in ("circle", "arc"):
        return Shape(
            type=shape_type,
            center=s.get("center"),
            radius=s.get("radius"),
        )
    # polygon or unknown → treat as polygon
    return Shape(type="polygon", points=s.get("points", []))
