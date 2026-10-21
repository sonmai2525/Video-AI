# V10 — Multimodal Story Director

V10 upgrades the local V9 story/reframe layer into a **story-first editing pass**.

## What is new

- Samples three keyframes per detected scene and writes scene contact sheets to `v10_storyboards/`.
- Fuses V9 moment score + V8 visual cues into a V10 story score.
- Selects the strongest scene as a **cold-open hook**, preserves chronological body flow, and reserves a strong late scene as payoff.
- Keeps V9 subject-aware `focus_x/focus_y` when clips are reordered.
- Supports an optional, provider-neutral Vision-Language Model JSON file. This allows a real multimodal model to add visible action descriptions, importance, surprise, clarity, and a short headline without coupling the repo to one API.
- Stores semantic/headline intent in the EDL for downstream text design.

## One-command local mode

```bash
python helpers/auto_viral_editor.py input.mp4 -o final.mp4 --target 20 --aspect 9:16
```

This works without a cloud VLM. It creates the V10 vision packet and uses local evidence.

## Optional real multimodal enrichment

Create JSON in this shape after reviewing the generated contact sheets:

```json
{"scenes":[{"scene_id":0,"description":"A cyclist lands a jump","action":"landing","importance":0.9,"surprise":0.8,"clarity":0.95,"headline":"THE LANDING"}]}
```

Then run:

```bash
python helpers/multimodal_story_v10.py input.mp4 edit/analysis.json edit/story.v9.json \
  --semantic edit/semantic.v8.json --vlm-json edit/vlm.json \
  -o edit/story.v10.json --edl edit/edl.json --apply --target 20
```

## Honest boundary

The repository does **not** pretend OpenCV can name arbitrary actions or understand a human narrative. Local mode ranks visible/audio evidence. Human-level descriptions require a multimodal model, supplied through the documented JSON contract. This keeps V10 testable, provider-neutral and safe to run offline.
