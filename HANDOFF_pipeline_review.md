# HANDOFF — Geometry pipeline → Fusion: review gate + fix #2–#5

> **Paths moved 2026-08-27.** The five parts now live in `tasks/<slug>/`
> (`autocad-bracket`, `base-boss`, `ex173`, `rocker-arm`, `step-bracket`), each with
> `spec.json` and `build/`. STEP exports moved out of git to
> `~/data/cad-exports/<slug>/`. `inspect_v5.py` and `render_generic.py` stayed at the
> repo root — they are part-agnostic. See `tasks/README.md` and
> `brain/31-cad-workspace.md`.

**From:** deepseek-v4-pro session (DSH, workspace /home/nik/dev/Extract-dimensions)
**Written:** after user said "context is quite full, kick it into a new session"

## TL;DR — what the next session must do

All 5 drawings from `Fusion360_MCP_Training/data/drawings/` were built in Fusion and exported to
STEP, but a **vision review (claude-opus-5) found only #1 fully matches** — #2–#5 have missing /
approximate features. The **corrected pipeline must include a per-part review gate with a vision
subagent** (this was the user's explicit callout; it IS documented — see §5). Fix #2–#5, gate each,
re-export.

## 1. Machine map (UPDATED — desktop is now the live Fusion host)

| Machine | Tailnet IP | State |
|---|---|---|
| **Desktop** `desktop-7tnrkpl` | `100.125.213.97` | **LIVE Fusion host.** Fusion 360 installed + `fusion360_mcp_bridge` add-in (HTTP bridge, 127.0.0.1:7634 loopback, runOnStartup). Driven via SSH tunnel + custom client. |
| **Laptop** `compname` | `100.73.157.46` | DEAD this session (user's connection problems; watchers timed out). Had `AutodeskFusionMCP` (Streamable MCP on :8765) — if it comes back, the `mcp__fusion360__*` tools work again. |

- **SSH:** `Großeel@100.125.213.97` (key auth). The desktop needs an **interactive login** (user RDP'd in) for Fusion to run.
- **Tunnel (restart in new session):** `ssh -N -L 7634:127.0.0.1:7634 Großeel@100.125.213.97` (was job bash-5).

## 2. Driving the desktop bridge

- **Client:** `/home/nik/dev/Extract-dimensions/desktop_fusion_client.py` — `status | py '<code>' | run <file.py> | bodies | design`.
- **Bridge API:** `GET /status` → `{"status":"ok"}`; `POST /command` with `{"command","params"}`. Commands: `get_active_design`, `get_bodies`, `get_sketches`, `export_design` (`format` stl|step|f3d|iges, `output_path` no-extension), `save_design`, **`run_python`** (pre-binds `adsk/app/ui/design/math/json`; set `result` to return JSON).
- **NO capture_viewport on the bridge.** To render: `vp.setVisualStyle(Shaded)` → `vp.goHome()` → `vp.isometricView()` → `vp.fit()` → `vp.saveAsImageFile("D:\\fusion_parts\\<name>.png", 1000, 750)`.
- **Pull files back:** scp FAILS on the `ß` username. Use base64 pipe:
  `ssh Großeel@100.125.213.97 "powershell -NoProfile -Command \"[Convert]::ToBase64String([IO.File]::ReadAllBytes('D:/fusion_parts/<f>.png'))\"" | sed '1s/^\xEF\xBB\xBF//' | tr -d '\r\n' | base64 -d > <f>.png`

## 3. Fusion API gotchas (ALL learned this session — read before touching anything)

1. Desktop doc is **PARAMETRIC** (designType=1). **Cleanup MUST delete timeline features:** `tl.item(i).entity.deleteMe()` in reverse. `b.deleteMe()`/`s.deleteMe()` fail silently in parametric → leftover bodies contaminate later builds (this caused a false "DIFFERENT" review on #1).
2. `setDistanceExtent(True, d)` = **d EACH SIDE** (total 2×d). For 20 mm total symmetric use `cm(10)`. `setDistanceExtent(False, d)` = one-sided +normal.
3. **XZ plane mapping:** sketch `(sx,sy) → (sx, 0, −sy)` (3D (X,0,Z) needs sketch (X,−Z)). Use `modelToSketchSpace` or the explicit mapping.
4. `addByCenterStartSweep`: +sweep = CCW, −sweep = CW. `startSketchPoint/endSketchPoint` are in CCW order regardless of draw direction. For exact 180° arcs, `atan2(cross,dot)` returns +π when you want −π — hardcode the sign.
5. **Arc junction points must be EXACTLY on the circles** (full-precision tangency math, not 3-decimal values) or the profile won't close.
6. Offset-start extrude: `inp.startExtent = OffsetStartDefinition(cm(offset))` + `inp.setOneSideExtent(DistanceExtentDefinition(cm(d)), PositiveExtentDirection)`.
7. Fillet: `ff.createInput()` → `fi.addConstantRadiusEdgeSet(edges, ValueInput, tangentChain)` → `ff.add(fi)` (on the INPUT, not the collection). Two fillets on perpendicular edges that meet can conflict — add both edge sets in ONE input.
8. `ConstructionPlaneInput.setByThreePoints` FAILS (InternalValidationError) — avoid.
9. All 5 bodies verified `isSolid == true` (valid solids).

## 4. Build scripts (all in /home/nik/dev/Extract-dimensions/, all self-cleaning + timeline cleanup)

`rocker_arm_build.py` (cleanup FIXED; verified 1 body, vol 115627.3) · `base_boss_build.py` · `step_bracket_build.py` · `tasks/autocad-bracket/build/autocad_bracket_build.py` · `ex173_build.py` · driver `desktop_fusion_client.py`

## 5. Review-with-subagent — THE CORRECTED PIPELINE STEP (user callout, do NOT skip)

Documented in `fusion-training-data/workflows/workflows.md` (workflow #1 "Vision-Encode Reference Images"; `capture_viewport` → vision agent gate) and the tool catalog `fusion_validate_drawing_vs_model` / `fusion_validate_mesh` (band-D samples). **I skipped this per-part during the builds — that's the mistake.** The gate per part:

1. Build (run script) → verify body solid + bbox.
2. Render via `saveAsImageFile` (isometric + a front/top view).
3. Spawn `claude-opus-5` via the **workflow tool**: `agent(prompt, {provider:'anthropic', model:'claude-opus-5'})` with `read_image` of BOTH the drawing and the render; prompt must say: Fusion is Y-up vs drawing Z-up (rotation is a convention, not an error); judge FEATURE PRESENCE.
4. Fix → re-render → gate passes → export STEP.

## 6. Review results (current state) — what to fix

| # | Part | Verdict | Missing / wrong |
|---|---|---|---|
| 1 | rocker_arm | ✅ MATCH | none (all 12 features; first "DIFFERENT" was render contamination) |
| 2 | base_boss | ⚠️ | **both R30 web fillets** (F2 failed w/ edge conflict), **15×3 front notch**; boss Ø30-vs-Ø25 ambiguous |
| 3 | step_bracket | ⚠️ | **stepped tier on arm** (I made a top-notch instead of raised tier), **slot between legs**, **rounded foot** (all in the truncated spec part); core web/lug/arm/Ø30-bore OK |
| 4 | autocad_bracket | ⚠️ | **S2 obround slot (135°) cut FAILED** (sketch profile didn't form — verify tangent-line obround), **outer profile is a disc** not open 3-lobe; Ø16 bore IS cut (verified), S1 slot OK |
| 5 | ex173 | ⚠️ | skeleton: **3-lobe base + 3×Ø10 mounting holes + central Ø32/Ø19 tower + 2×45° chamfer** missing |

STEP exports (pre-fix): `D:\fusion_parts\*.stp` (rocker_arm 126 KB, ex173 37 KB, base_boss 25 KB, autocad_bracket 25 KB, step_bracket 19 KB). Renders: `/home/nik/dev/Extract-dimensions/review/*_v2.png`.

## 7. Reference material

- Drawings: `/home/nik/dev/Fusion360_MCP_Training/data/drawings/` (example5-2094245636.png, OIP-1099189824.jpg, OIP-479997622.jpg, OIP-652393864.jpg, OIP-366831756.jpg).
- Full specs from claude-opus-5 reads (in prior session context): rocker_arm exact tangency (hub O R40, boss B(12,√5796) R10, R100 C2(±60,0), R35 C1(±51.482,±54.540); 8-arc profile); base_boss (95×40×15 base, upright, slot R12.5, boss Ø30, R30×2); step_bracket (web P1(30,0)..P7(50,0), R20 lug at (75,65), arm X0-45 Y39-65, Ø30 bore); autocad_bracket (C1(0,0) Ø40/Ø20, C2(−10,−48.3) Ø50/Ø16, C3(+46.2,−46.2), S1 R70/42°, S2 135°/30/R8, R85/R30/R32/R25/R15/R8, thickness 10 assumed); ex173 (Ø108 flange R54, 3×Ø16 lugs R50/120°, body Ø44→Z40, neck Ø25→Z75, bore Ø19, side boss Ø32 @Z20 with Ø8 cross-bore — flagged).
- Pipeline docs: `fusion-training-data/README.md` + `workflows/workflows.md` + `Geometry_2D_to_3D_Pipeline.md` (in `/home/nik/dev/Model_Training_Knowledge/`).

## 8. Next steps (ordered)

1. Restart SSH tunnel; confirm bridge up (`desktop_fusion_client.py status`).
2. Fix #4: S2 obround slot (rebuild the obround so a profile forms — e.g. two R8 circles + two tangent lines, then select the enclosed region; or a rounded-rectangle via offset). Re-render, gate.
3. Fix #2: add BOTH R30 fillets in one fillet input; add the 15×3 front notch. Re-render, gate.
4. Re-read #3 (step_bracket) and #5 (ex173) drawings via claude-opus-5 for the missing features, finish builds, gate.
5. Re-export all 5 STEPs to `D:\fusion_parts\` after each passes the gate.
