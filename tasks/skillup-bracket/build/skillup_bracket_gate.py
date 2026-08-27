# Gate: compare built skillup_bracket renders against the source drawing.
# Runs the vision comparison via modlens on the rendered PNGs + drawing.
# Usage (host side, not Fusion):
#   python3 skillup_bracket_gate.py <render_dir> <drawing.jpg>
#
# Expected drawing dims (from output/skillup_bracket.json):
#   145 length · 90 height · 72/50/48/36/30/25/24 steps · Ø24 hole · R30/R12 · 6/12
import json
import sys

from pathlib import Path
# task folder lives at <repo>/tasks/<slug>/build/, so the repo root is three up
REPO_ROOT = Path(__file__).resolve().parents[3]

def main():
    render_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    drawing = sys.argv[2] if len(sys.argv) > 2 else "skillup_bracket.jpg"

    with open(REPO_ROOT / "output" / "skillup_bracket.json") as f:
        spec = json.load(f)

    print("GATE: skillup bracket")
    print("  drawing :", drawing)
    print("  renders :", render_dir + "/skillup_bracket_{iso,top,side}.png")
    print("  spec dims:")
    for d in spec["dimensions"]:
        print("    -", d["label"], d["value"], d["unit"])
    print()
    print("Manual step (vision gate): for each render, run")
    print("  modlens_read_image(<render>) with prompt:")
    print("   'Transcribe every dimension number visible on this CAD model render,'")
    print("   'then compare against the drawing spec: 145/90/72/50/48/36/30/25/24/Ø24/R30/R12.'")
    print("   'Report matches and mismatches per dimension.'")
    print("Verdict: MATCH only if all dims agree; else list diffs and adjust *_MM params")

if __name__ == "__main__":
    main()
