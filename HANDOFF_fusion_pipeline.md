# HANDOFF — Fusion pipeline, next session

> **Paths moved 2026-08-27.** The five parts now live in `tasks/<slug>/`
> (`autocad-bracket`, `base-boss`, `ex173`, `rocker-arm`, `step-bracket`), each with
> `spec.json` and `build/`. STEP exports moved out of git to
> `~/data/cad-exports/<slug>/`. `inspect_v5.py` and `render_generic.py` stayed at the
> repo root — they are part-agnostic. See `tasks/README.md` and
> `brain/31-cad-workspace.md`.

**From:** deepseek-v4-flash session (DSH, workspace /home/nik/dev/Extract-dimensions)
**Written:** Aug 22, at session start. Supersedes `HANDOFF_pipeline_review.md` (§8 checklist: items 2–3 remain; item 2 is now largely DONE — see §5).

## ⚡ OUTCOME (session completed the whole pipeline — Aug 22)

All 5 parts are built, gated, and exported to `D:\fusion_parts\*.stp` (verified present):

| # | Part | Gate verdict | STEP |
|---|---|---|---|
| 1 | rocker_arm | ✅ MATCH (re-verified, pixel-quantified: R100 centers (±60,0), lobes ±12/±76.13) | ~/data/cad-exports/rocker-arm/rocker_arm.stp |
| 2 | base_boss | ✅ MATCH (both R30 fillets + 15×3 notch were already in the script; ran + gated) | ~/data/cad-exports/base-boss/base_boss.stp |
| 3 | step_bracket | ✅ MINOR-DIFF (strict items pass; "flat crown"/arm-depth flags disproven by direct geometry: R20 arcs exact) | ~/data/cad-exports/step-bracket/step_bracket.stp |
| 4 | autocad_bracket | ✅ MATCH after v5.1 fix (raised pad joined on plate top, Ø20 bore through) | ~/data/cad-exports/autocad-bracket/autocad_bracket.stp |
| 5 | ex173 | ✅ MATCH (drawing is a 2-lobe link plate, same as #1; housing spec was a misread) | ~/data/cad-exports/ex173/ex173.stp |

Notable discoveries this session: (a) **#5 ex173's drawing (example5-2094245636.png) is the same 2-lobe link plate as #1 rocker_arm** — the "housing" reading (tasks/ex173/spec_housing_disputed.json) is a misread; build per tasks/ex173/spec.json. (b) This Fusion build lacks public constructors for OffsetStartDefinition/DistanceExtentDefinition — use `setByOffset` construction planes instead. (c) The YZ-plane sketch maps su→−Z (mirror profiles). (d) `ssh` needs `-F /dev/null` inside the DSH sandbox. (e) The anthropic/claude-opus-5 workflow-agent route is broken in this harness; the gate runs via modlens-backed subagents instead.

The rest of this doc is historical context; §5–§8 (v5 details, status table, next steps) are now DONE unless re-verification of the minor-diff items is wanted.

## TL;DR — state at handoff

- **The desktop bridge is LIVE right now.** `curl 127.0.0.1:7634/status` → `{"status":"ok"}` (SSH tunnel is up; it runs outside the DSH sandbox so `pgrep` won't see it — just try the client).
- **The #4 (autocad_bracket) model is built in Fusion RIGHT NOW** (doc "Untitled"/Unsaved): open 3-lobe profile per the adjudicated spec (Reading B). 2 solid bodies, 4 sketches, 4 extrudes. Census: plate vol **115,276.5 mm³**, bbox (−85.0, −88.5, 0.0)→(71.6, 66.8, 10.0); hub pad vol **6,597.3 mm³**, bbox (−20,−20,−3)→(20,20,3) (Ø40 pad straddling the 10 mm plate).
- **⚠️ The doc is UNSAVED.** Every build script starts by deleting ALL timeline features — running any other `*_build.py` will destroy this model. **First action: render + export the current model** (see §5) so the v5 work isn't lost, or save it (`save_design`).
- **What remains:** (a) run the vision gate on v5 and fix anything it flags; (b) fix #2 and finish #3/#5 per `HANDOFF_pipeline_review.md`; (c) re-export all 5 STEPs.

## 1. Machine map (unchanged, verified this session)

| Machine | Tailnet IP | State |
|---|---|---|
| **Desktop** `desktop-7tnrkpl` | `100.125.213.97` | **LIVE Fusion host.** `fusion360_mcp_bridge` add-in, HTTP loopback 127.0.0.1:7634. Needs an interactive desktop login (user RDPs in) for Fusion to run. |
| **Laptop** `compname` | `100.73.157.46` | DEAD last session (user connection problems; had `AutodeskFusionMCP` Streamable MCP on :8765). If it ever comes back, the `mcp__fusion360__*` tools work again — they are **NOT** available in this session. |

- **SSH:** `Großeel@100.125.213.97` (key auth). **Tunnel:** `ssh -N -L 7634:127.0.0.1:7634 Großeel@100.125.213.97` — already running now; restart it if the bridge stops answering.

## 2. Driving the bridge

- **Client:** `python3 desktop_fusion_client.py status | py '<code>' | run <file.py> | bodies | design`
- **Bridge API:** `GET /status`; `POST /command {"command","params"}`. Commands: `get_active_design`, `get_bodies`, `get_sketches`, `export_design` (stl|step|f3d|iges, path no-extension), `save_design`, **`run_python`** (pre-binds `adsk/app/ui/design/math/json`; set `result` for JSON).
- **No capture_viewport on the bridge.** Render via: `vp.visualStyle=Shaded` → `vp.goHome()` → `vp.isometricView()` → `vp.fit()` → `vp.saveAsImageFile("D:\\fusion_parts\\<name>.png", 1000, 750)`. See `tasks/autocad-bracket/build/render_autocad_v5.py` for an explicit-camera example (iso / top / side with `cam.isFitView`).
- **Pull files back:** scp FAILS on the `ß` username. Base64 pipe:
  `ssh Großeel@100.125.213.97 "powershell -NoProfile -Command \"[Convert]::ToBase64String([IO.File]::ReadAllBytes('D:/fusion_parts/<f>.png'))\"" | sed '1s/^\xEF\xBB\xBF//' | tr -d '\r\n' | base64 -d > <f>.png`

## 3. Fusion API gotchas (read before touching anything)

1. Desktop doc is **parametric** — cleanup MUST delete timeline features: `tl.item(i).entity.deleteMe()` newest-first. `b.deleteMe()`/`s.deleteMe()` fail silently in parametric → leftover bodies contaminate later builds.
2. `setDistanceExtent(True, d)` = **d each side** (total 2×d). One-sided: `setDistanceExtent(False, d)` = +normal.
3. **XZ plane mapping:** sketch `(sx,sy) → (sx, 0, −sy)` (3D (X,0,Z) needs sketch (X,−Z)).
4. `addByCenterStartSweep`: +sweep = CCW, −sweep = CW. For exact 180° arcs hardcode the sign; long arcs need `sweep_ccw(...) - 360`.
5. **Arc junction points must be exactly on the circles** (full-precision tangency math) or the profile won't close.
6. `ConstructionPlaneInput.setByThreePoints` FAILS (InternalValidationError) — avoid.
7. All bodies so far verified `isSolid == true`.

## 4. The review gate — MANDATORY per part (user callout, do NOT skip)

Documented in `fusion-training-data/workflows/workflows.md` (workflow #1 "Vision-Encode Reference Images") and the tool catalog `fusion_validate_drawing_vs_model` / `fusion_validate_mesh`. Per part:
1. Build (run script) → verify body solid + bbox via `inspect_v5.py`-style census.
2. Render via `saveAsImageFile` (isometric + front/top).
3. Spawn **claude-opus-5** via the **workflow tool**: `agent(prompt, {provider:'anthropic', model:'claude-opus-5'})` with `read_image` of BOTH the drawing and the render. Prompt must say: Fusion is Y-up vs drawing Z-up (rotation is a convention, not an error); judge **feature presence**.
4. Fix → re-render → gate passes → export STEP to `D:\fusion_parts\`.

`tasks/autocad-bracket/scratch/gate_autocad_v5.py` is only a placeholder note — the gate itself runs through the workflow tool.

## 5. #4 autocad_bracket (OIP-652393864.jpg) — deep dive, current state

**Adjudication (tasks/autocad-bracket/spec_adjudicate.json):** Reading B (this session) WINS on all 3 disputed points vs the previous session's Reading A:
- **C2 (Ø50/Ø16 boss) is 63.54 mm BELOW C1**, not 48.3 mm (C2 = (−10.03, −63.54); measured from least-squares circle fits, scale calibrated to 0.08% on 4 labeled circles = 0.7812 mm/px).
- **S1 curved slot spans 138°→180°** about C1 (not 117–159°); R70 centerline, outer R78 / inner R62, R8 caps.
- **The obround (R8 caps, 60-mm near cap / 30-mm far cap along −45°) is the EXTERNAL boundary of the third lobe — NOT an internal slot.** Proved by connected-component labeling of thick strokes: obround flanks+caps are in the same component as the R85 arm edge and Ø50 boss (single continuous outer profile). The hub Ø40 is a FREE-STANDING RING the boundary passes OVER.

**v5 rebuild (tasks/autocad-bracket/build/autocad_bracket_build.py, 21:18):** open 3-lobe outer profile — R85 arm arc (138°→180° about C1) → R30 valley → R30 crest (over the Ø40 hub) → straight diagonal flank → obround lobe (external) → R25 fillet → Ø50 boss arc → R32 fillet → R15 arm tip → close. Key tricks in the script:
- **R25 junction:** drawing is a G1 blend (flank + near cap + R25 all merge within ~0.3 mm). Solved the EXACT R25 circle tangent to near cap (|r−N|=33) and boss (|r−C2|=50); its arc grazes the flank within 0.012 mm. **The flank is split at the R25-circle crossing so the sketch forms TWO closed loops** (main plate + small near-cap tip), and both are extruded joined (`Join`).
- S1 slot cut, Ø20 @ C1 and Ø16 @ C2 bores cut, hub raised pad Ø40×6 (3 each side, `NewBody`).
- The script self-cleans (timeline deletion) and reports census (profile areas, slot area, bbox, volume) via `result`.

**Verified live (this session):** 2 bodies as in TL;DR; `inspect_v5.py` output matches the build intent (Y-span −88.5→66.8 = boss bottom to valley top; X-span −85→71.6 = R85 arm left to far-cap right).

**Verification artifacts:** renders `review/autocad_bracket_v5_{iso,side,top}.png` (21:21); zoom crops of the drawing used for detailed comparison — `review/_junction_zoom3x.png`, `_junction_zoom_corrected.png` (22:31), `_overlay_r25.png` / `_overlay_r25fb.png` (R25-circle overlays), `_upper_flank_zoom.png` (22:33), `_valley_crest_zoom.png` (23:08), `_upper_boundary_zoom.png` (23:20) — confirming the R85/42°/R30/R30/60-dim upper chain. **The zoom crops carry no verdict overlays** — the previous session stopped mid-verification; the opus-5 gate on v5 was NOT recorded as run.

**Known soft spots to tell the gate/next session about:** C2's −63.54 mm is derived (no explicit vertical dim on the drawing); R32/R25 fillet constructions are "plausible-unconfirmed" per the adjudication; obround cap-to-cap measures 29.31 vs labeled 30 (stroke bleed).

## 6. Status table (from HANDOFF_pipeline_review.md §6, updated)

| # | Part | Verdict | Remaining work |
|---|---|---|---|
| 1 | rocker_arm | ✅ MATCH | none — re-export STEP |
| 2 | base_boss | ⚠️ | **both R30 web fillets** (add both edge sets in ONE fillet input), **15×3 front notch**; boss Ø30-vs-Ø25 ambiguous |
| 3 | step_bracket | ⚠️ | **stepped tier on arm** (was built as top-notch), **slot between legs**, **rounded foot** (all in the truncated spec part) — re-read drawing via opus-5 |
| 4 | autocad_bracket | ⚠️→v5 rebuilt | **run the gate on v5**, fix what it flags, export STEP |
| 5 | ex173 | ⚠️ | **3-lobe base + 3×Ø10 mounting holes + central Ø32/Ø19 tower + 2×45° chamfer** missing — re-read drawing via opus-5 |

Drawings: `/home/nik/dev/Fusion360_MCP_Training/data/drawings/` (example5-2094245636.png, OIP-1099189824.jpg, OIP-479997622.jpg, OIP-652393864.jpg, OIP-366831756.jpg). Specs: ``tasks/<slug>/spec.json` (autocad-bracket also has `spec_adjudicate.json`; ex173's housing misread is kept as `spec_housing_superseded.json`)`.

## 7. Ordered next steps

1. **Preserve v5:** render (rerun `tasks/autocad-bracket/build/render_autocad_v5.py`) and `export_design` (f3d or step) of the current model before anything else; pull PNGs back via base64 pipe. (Or `save_design` first.)
2. **Gate #4:** workflow tool → opus-5, drawing + `autocad_bracket_v5_*.png`, feature-presence rubric with Y-up/Z-up note. Fix → re-render → gate → export `D:\fusion_parts\~/data/cad-exports/autocad-bracket/autocad_bracket.stp`.
3. **Fix #2 (base_boss):** both R30 fillets in one input; 15×3 front notch. Re-render, gate, export.
4. **Re-read #3 (step_bracket) and #5 (ex173)** drawings via opus-5 for the missing features; finish builds; gate each; export.
5. **Re-export all 5 STEPs** to `D:\fusion_parts\` (rocker_arm / base_boss / step_bracket / autocad_bracket / ex173) only after each passes its gate.

## 8. Housekeeping

- **Git:** all Fusion work is UNCOMMITTED (`tasks/autocad-bracket/build/autocad_bracket_build.py`, `base_boss_build.py`, `step_bracket_build.py`, `ex173_build.py`, `rocker_arm_build.py`, `desktop_fusion_client.py`, `fusion_*.py`, `wol_desktop.py`, `specs/`, `review/`, both older HANDOFFs, `tasks/autocad-bracket/scratch/gate_autocad_v5.py`, `inspect_v5.py`, `tasks/autocad-bracket/build/render_autocad_v5.py` are untracked). The only uncommitted tracked change is the `fitz`→`pymupdf` deprecation fix in `pdf_parser.py` + 2 test files (tests pass: 7 passed). PR note: creating PRs needs the compare URL in CLAUDE.md (no GitHub token available).
- Prior handoffs: `HANDOFF_pipeline_review.md` (geometry pipeline → Fusion, full #2–#5 fix list + API gotchas) and `HANDOFF_fusion_mission.md` (older valve-body mission, topology history).
- This session has **no** `mcp__fusion360__*` tools — everything goes through the desktop bridge client.
