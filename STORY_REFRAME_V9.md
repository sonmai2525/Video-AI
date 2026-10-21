# V9 — Story Understanding + Smart Reframe

V9 adds a provider-neutral story/reframing layer after V8 Semantic Vision.

## What changed
- Samples 5 frames per scene instead of trusting a single center frame.
- Finds a likely subject using face-priority detection and saliency fallback.
- Fuses visual motion, face presence, duration, beat entry and confidence into a `moment_score`.
- Emits story-role hints: `hook_candidate`, `highlight`, `support`, `payoff_candidate`.
- Writes `focus_x` / `focus_y` into render ranges.
- `render.py` now uses those coordinates for subject-aware 9:16/16:9/1:1 cropping instead of fixed center crop.
- Strong moments may receive subtle zoom; weak moments have unnecessary camera motion removed.

## One-command pipeline
```bash
python helpers/auto_viral_editor.py input.mp4 -o final.mp4 --target 20 --aspect 9:16
```

Artifacts include `story.v9.json` plus the V5/V6/V8 plans and QC reports.

## Important boundary
Local V9 provides useful visual/audio fusion and smart reframing, but it does not pretend to understand arbitrary scenes at human level. The JSON contract is intentionally ready for a future vision-language provider that can add object/action descriptions and narrative summaries.
