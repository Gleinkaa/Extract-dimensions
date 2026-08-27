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

Migrated so far: `skillup-bracket`. Still at the root and awaiting the same
treatment: `autocad_bracket`, `base_boss`, `ex173`, `rocker_arm`, and the
`*_v5` gate/inspect/render trio.
