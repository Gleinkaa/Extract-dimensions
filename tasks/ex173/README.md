# ex173 — which drawing is this?

Two sessions disagree about what `example5-2094245636.png` / `OIP-366831756.jpg`
actually shows, and the disagreement is unresolved as of 2026-08-27:

- `spec.json` — **2-lobe link plate**, the same part as `rocker-arm`.
  `HANDOFF_fusion_pipeline.md` calls the housing reading a misread and says to
  build from this.
- `spec_housing_disputed.json` — **3-lobe housing** with 3x O10 mounting holes, a
  central O32/O19 tower and 2x 45 deg chamfers.
  `tasks/skillup-bracket/REVIEW_5_MODELS.md` says the opposite: that the housing
  spec is right, that discarding it was the error, and that the exported
  `ex173.stp` is invalid because of it.

`build/ex173_build.py` currently builds the 2-lobe reading.

**Do not build this part until the drawing has been re-read and the dispute
settled.** Whichever way it goes, keep the losing spec — the point of having both
files is that this argument has already happened twice.
