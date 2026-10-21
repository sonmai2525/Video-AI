# V5 — AI Director

V5 adds a director stage before rendering. It inspects a representative frame from every detected scene and generates `visual_text_events` automatically.

## What it decides
- safest text region using negative-space / edge-density scoring
- face avoidance when OpenCV face detection is available
- hook treatment on the opening scene
- CTA treatment on the final scene
- restrained motion (`rise`, `pop`, `slide_*`, `drift`) based on scene length and beat proximity
- confidence + scene inspection data so an agent can review weak decisions

## Run
```bash
python helpers/analyze_short.py input.mp4 -o edit/analysis.json
python helpers/make_short_edl.py edit/analysis.json -o edit/edl.json --target 20 --aspect 9:16
python helpers/ai_director.py input.mp4 edit/analysis.json -o edit/director.v5.json --edl edit/edl.json --apply
python helpers/render.py edit/edl.json -o final.mp4 --build-subtitles
```

## Contract for a stronger multimodal model
The local director deliberately separates **analysis** from **rendering**. A multimodal model can inspect richer frame samples and overwrite `visual_text_events` without changing `render.py`.

Each event can contain:
```json
{"start":0,"end":1.4,"layout":"top_left","motion":"rise","style":"hook","box":false,"icon":""}
```

The renderer remains deterministic. This prevents a vision model from directly inventing FFmpeg/ASS commands.

## Current boundary
V5 local mode understands geometry (faces, clutter, negative space, beats), not the semantic meaning of arbitrary imagery. True subject segmentation / text-behind-person remains a later matte/depth stage.
