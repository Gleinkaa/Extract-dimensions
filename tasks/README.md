# tasks/

One folder per job. See `brain/31-cad-workspace.md` for the full convention.

    tasks/<slug>/
    ├── HANDOFF.md    only while unfinished; deleted in the commit that lands the work
    ├── spec.md       dimensions, constraints, decisions - written before code
    ├── inputs/       source drawings, crops, measured references
    ├── build/        the runnable scripts
    ├── captures/     renders that prove the current state
    └── scratch/      probes and one-offs - deleted when the task lands

This replaces the old pattern of putting task files at the repo root with a
filename prefix (`skillup_bracket_build.py`, `_render.py`, `_gate.py`, ...).
That is a task folder expressed as a naming scheme, and it never cleans up:
before this change the root held ~40 files for six different parts and
`review/` had accumulated ~50 debug scripts from a single session.

Scripts that read repo-level paths must anchor on `__file__`, not the working
directory - a task folder is three levels down from the repo root:

    REPO_ROOT = Path(__file__).resolve().parents[3]

**Migration complete (2026-08-27).** Every part now has a folder:
`skillup-bracket`, `autocad-bracket`, `base-boss`, `ex173`, `rocker-arm`,
`step-bracket`. Slugs are hyphenated even though the scripts inside keep their
underscored filenames. `step-bracket` was migrated too — it was the same
root-prefix pattern and had simply been missed off the list.

Two files deliberately stayed at the repo root, because
`brain/31-cad-workspace.md` hoists shared reference out of task folders and both
are part-agnostic:

- `render_generic.py` — renders any design to `D:\fusion_parts\<name>_*.png`
- `inspect_v5.py` — body/volume/bbox census for any open design, despite the
  `_v5` name it picked up during the autocad-bracket work

`gate_autocad_v5.py` went to `autocad-bracket/scratch/` rather than `build/`: it
is a three-line stub that returns `{"note": "use workflow tool"}` and builds
nothing. The real gate runs through the workflow tool.

STEP exports left git for `~/data/cad-exports/<slug>/` and `*.stp` is now
ignored, per the convention's "exports are not committed" rule.
