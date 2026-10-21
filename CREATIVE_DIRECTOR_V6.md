# V6 Creative Director

V6 moves beyond text placement and makes **edit-level creative decisions** for short-form video.

## What it decides

- scene highlight score and keep/drop priority
- hook / highlight / support / payoff role
- faster pacing for weak shots and restrained slow-down for strong moments
- subtle `zoom_in` / `zoom_out` motion
- beat-aware cut endpoints
- transition intent (`hard_cut`, `beat_cut`, `impact_cut`)
- suggested SFX cues (`whoosh_soft`, `impact_light`, `tick`)
- global grade mood and music-mix strategy

The renderer now consumes `speed` and `motion` on each EDL range. Caption timing is automatically remapped when a range is sped up or slowed down.

## Full V6 flow

```bash
python helpers/analyze_short.py input.mp4 -o edit/analysis.json
python helpers/make_short_edl.py edit/analysis.json -o edit/edl.json --target 20 --aspect 9:16
python helpers/ai_director.py input.mp4 edit/analysis.json -o edit/director.v5.json --edl edit/edl.json --apply
python helpers/creative_director.py edit/analysis.json --director edit/director.v5.json --edl edit/edl.json --apply --target 20
python helpers/render.py edit/edl.json -o edit/final.mp4 --build-subtitles
```

## Important boundary

The local V6 director uses measurable signals: scene timing, beats and V5 visual geometry. It does **not** falsely claim semantic understanding of the story. A multimodal model can later override the same JSON plan with richer judgments such as "this is the reveal" or "keep the reaction shot".

Transition and SFX fields are currently explicit creative intents. Cuts, speed changes and camera motion render locally. Actual external sound-effect files require assets to be supplied/licensed and mixed in a later audio pass.
