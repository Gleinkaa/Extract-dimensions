# HANDOFF — SkillUP bracket (images.jpg), prepared kit

**From:** DSH session (workspace /home/nik/dev/Extract-dimensions)
**Written:** Aug 24 ~10:30, while Fusion was mid-update / UI-thread-blocked.

## Task
"Check the drawing" = build the **SkillUP CADD bracket** from `~/inbox/images.jpg`
(isometric, all mm) in **live Fusion** (MCP at `100.73.157.46:8765`, laptop `compname`),
then verify against the drawing.

## Drawing (vision-transcribed, 4x-upscaled read — authoritative)
145 base length · 72 base depth · 12 base thickness · **80 LEFT block height**
(48+40 steps, 24 upper step width) · **Ø24 through-hole @ offset 30x / 36y above base** ·
R30 left-edge arc · R12 fillet near hole · R6 base corners · 25 right lower step · 6/12 details ·
"Dimensions in mm" · SkillUP logo.
⚠️ **Isometric only** — orthographic topology still partially ambiguous; build script
geometry is the corrected interpretation to verify via build → render → gate.

## Kit prepared (this session)
| File | Role |
|---|---|
| `skillup_bracket.jpg` / `.pdf` / `skillup_bracket_x4.png` | staged inputs (×4 upscale for vision) |
| `output/skillup_bracket.json` | 17 dims, method `modlens-ai-x4`, extrude 72 |
| `output/skillup_bracket.scad` | parametric 2D profile |
| `skillup_bracket_build.py` | Fusion build: base 145×12×72 + LEFT block 24×80 @X0, Ø24 bore @(30,48), R30 left-edge fillet, R6 base corners, R12 top fillet — **all `*_MM` params** for adjustment |
| `skillup_bracket_render.py` | iso/top/side renders → `D:\fusion_parts\` |
| `skillup_bracket_verify.py` | census: bodies/bbox/volume/feature health |
| `skillup_bracket_gate.py` | gate checklist vs extracted spec |
| `review/crop_{left,right,bottom,center}_x4.png` | region crops used for the corrected read |

## Fusion state at handoff
- MCP add-in healthy: `/health` 200, `tools/list` 11 tools, handshake OK (2025-11-25).
- **Every `tools/call` times out** — Fusion UI thread blocked (was mid-update at 10:2x).
  Watcher `fusion_watch.py` polls `list_scripts`/20s; prints `FUSION_READY` when free.
- Design was **empty/untitled** (census: DOC Untitled, 0 bodies) — nothing to preserve.

## API route note
`ai_extractor.py` now supports `ANTHROPIC_OAUTH_TOKEN` (from
`~/.dsh/.credentials.yaml`) as `auth_token`. Direct API calls are **429 rate-limited**;
the working vision route is **modlens** (used for all transcription here).

## Next steps once FUSION_READY
1. `fusion_census.py` → confirm design state.
2. Push `skillup_bracket_build.py` via `execute_python` (read file → send as `code`).
3. `skillup_bracket_verify.py` → check bbox ≈ (0..145, 0..92, 0..72) mm, 1 body, health ok.
4. `skillup_bracket_render.py` → pull 3 PNGs → vision-gate vs drawing (use `skillup_bracket_x4.png` as reference), adjust `*_MM` and rebuild.
5. Offer STEP export.
