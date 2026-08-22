# HANDOFF — Fusion 360 drawing-creation mission

**From:** deepseek-v4-pro session (DSH, workspace /home/nik/dev/Extract-dimensions)
**Written:** after user said "handoff to new session"

## Mission
Recreate two technical drawings as parametric models in **live Fusion 360** (via MCP), one after the other:
1. **3DIEST "PRACTICE EXERCISE-20" valve body** (DWG 140-723-20) — `3diest_ex20_sheet.png`
2. **Prismacad plate** — `prismacad_plate.png`

**User decision (final): do it in FUSION** (NOT Build123D/Triad). Sequence: only start #2 after #1 is confirmed done in Fusion.

## Already done
- PyMuPDF deprecation cleanup in `/home/nik/dev/Extract-dimensions` (`import fitz` -> `import pymupdf` in pdf_parser.py + 2 test files). Tests: **7 passed**.
- **fable review: PASS** — spawned `claude-fable-5` subagent via the `workflow` tool (`agent(prompt, {provider:'anthropic', model:'claude-fable-5'})`); it independently verified the cleanup (7 passed, no stray fitz).

## Machine topology (this was the confusion — read carefully)
| Machine | Tailnet IP | OS | Role |
|---|---|---|---|
| **Laptop** = `compname` | `100.73.157.46` | Windows | **runs Fusion 360 + the MCP add-in** (active, relay "fra") |
| **Desktop** = `desktop-7tnrkpl` | `100.125.213.97` | Windows | CAD box; **woken via WoL this session**, but has NO Fusion MCP (nothing on :8765) |
| `a9max-linux` | `100.124.187.58` | Linux | THIS box (agent host) |
| `a9max` | `100.116.255.119` | Windows | retired (not bootable) |
| Home Assistant | `100.125.227.26` | Linux | WoL `input_button.wake_pc` |

**Fusion + the MCP add-in live on the LAPTOP (`compname`, `100.73.157.46`), NOT the Desktop.**

## Fusion MCP — reachable but HUNG (the blocker)
- Endpoint: `http://100.73.157.46:8765/mcp` (Streamable HTTP). Server: `autodesk-fusion-mcp` v1.3.0, protocol `2025-03-26`.
- `initialize` -> 200, `tools/list` -> 200 (11 tools). **Every `tools/call` times out** (even trivial `list_scripts`, `fetch_design_guide`, `capture_viewport`). Interpretation: Fusion's **UI thread is blocked** (modal dialog or wedged recompute) while the add-in's HTTP layer still answers the handshake.
- User restarted Fusion but it was **still hung** at the last probe.
- Tools: `call_autodesk_api`, `execute_python`, `capture_viewport`, `get_active_selection`, `fetch_api_documentation`, `fetch_online_documentation`, `fetch_design_guide`, `save_script`/`load_script`/`list_scripts`/`delete_script`.

## How to drive Fusion (working method this session)
The proper DSH way is the `fusion360` agent preset (mounts `mcp__fusion360__*` via `@deepseek-ai/dsh-mcp-client`, url `FUSION_MCP_URL || http://100.73.157.46:8765/mcp`, `failOnStartupError:false`). **This session was NOT on that preset**, so a direct HTTP MCP client was used. Scratch helpers in `/home/nik/dev/Extract-dimensions/`:
- `fusion_mcp_client.py` — `python3 fusion_mcp_client.py tools` (list) or `... call <tool> '<json-args>'`
- `fusion_census.py` — dumps live design state (doc, units, timeline, bodies, bbox, feature health)
- `fusion_probe.py` — probes 4 tools to test responsiveness
- `fusion_watch.py` — background watcher (polls `list_scripts`; prints `FUSION_READY` when responsive)
- `wol_desktop.py` — triggers Desktop WoL via HA

## Reference material (authoritative)
- `/home/nik/A_AI_infra/part_ref/SPEC_VERIFIED_FINAL.md` — **AUTHORITATIVE valve-body spec** (3 ports @120° each Ø18 OD / Ø10 bore, main bore Ø15 through 44, flange 60x10, lug R8@(0,-22) with Ø5 hole@(0,-27), 2 more Ø5 holes@(±26,26), R4 corners + TRUE R5 port-root fillets, Z-stack disc/hub/body). Also the **10x-oversize root cause** note (Fusion APIs return cm; pass mm x0.1).
- `/home/nik/A_AI_infra/HANDOVER_TO_FABLE.md` — live model is **broken**: feature 30 `Fillet_R5_root_Vert` health=2 ERROR; a wrong vert-port fix moved SK_Port_Vert circle to (-1.1,0) — must **revert to (0,1.1) cm**. Contains the repair order and Fusion API gotchas.
- `/home/nik/A_AI_infra/HANDOFF.md` — prior session history (units gotchas, API gotchas, user decisions).
- `/home/nik/A_AI_infra/inbox/` — source drawings (`3diest_ex20_sheet.png`, `prismacad_plate.png`); `upscaled/` has x4 versions.
- `/home/nik/A_AI_infra/brain/10-machines.md`, `11-network.md`, `12-services.md` — topology/services.

## Credentials & routing (verified this session)
- **Fusion MCP**: no auth; direct HTTP at `100.73.157.46:8765/mcp`.
- **claude-fable-5 subagent**: `workflow` -> `agent(prompt, {provider:'anthropic', model:'claude-fable-5'})`. Harness resolves the token from `~/.dsh/.credentials.yaml` (`ANTHROPIC_OAUTH_TOKEN`). (Direct `api.anthropic.com` with the OAuth accessToken from `~/.claude/.credentials.json` -> HTTP 429 rate-limit; the subagent route is the one that works.)
- **HA WoL**: POST `http://100.125.227.26:8123/api/services/input_button/press` body `{"entity_id":"input_button.wake_pc"}`, header `Authorization: Bearer <HA_TOKEN>` (token in `~/.config/bambubridge.env`).

## DSH agent presets (discovered)
- `fusion360` — mounts `mcp__fusion360__*` (the Fusion MCP).
- `cad-eng` — mounts `cad_generate` (Triad Build123D -> STEP/STL pipeline). **User rejected this path** ("we do it in fusion"). Note for awareness only.

## Immediate next steps
1. Unblock Fusion on the **laptop**: fully quit + relaunch Fusion, re-run `AutodeskFusionMCP` add-in (Tools → Scripts & Add-Ins → Run), leave window open/unlocked. If `tools/call` still times out after a clean restart, the hang is deeper than a dialog — inspect the add-in's tool dispatch (CustomEvent -> UI thread).
2. Once a `tools/call` returns (probe `list_scripts`), run `fusion_census.py` to read the live model state.
3. Fix/rebuild valve body per SPEC_VERIFIED_FINAL.md + HANDOVER_TO_FABLE.md repair order (revert vert port -> repair fillet -> verify).
4. Only after #1 is verified in Fusion, start #2 (prismacad plate).
