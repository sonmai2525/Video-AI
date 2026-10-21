# Text Engine V4 — Visual/Kinetic captions

V4 builds on V3 semantic captions and adds per-scene layout, motion, icon accents and optional text panels.

## Default mode
`visual_dynamic` is now the default when `--build-subtitles` is used.

```bash
python helpers/render.py edit/edl.json -o final.mp4 --build-subtitles --caption-style visual_dynamic
```

## visual_text_events
An AI/vision analysis stage can describe where text should go without changing the renderer:

```json
{
  "caption_style": "visual_dynamic",
  "visual_text_events": [
    {"start": 0.0, "end": 1.2, "style": "hook", "layout": "upper", "motion": "rise", "icon": "🔥"},
    {"start": 1.2, "end": 2.5, "layout": "left", "motion": "slide_left"},
    {"start": 2.5, "end": 4.0, "style": "number", "x": 0.72, "y": 0.38, "motion": "pop", "box": true}
  ]
}
```

Layouts: `center`, `upper`, `lower_safe`, `left`, `right`, `top_left`, `top_right`.
Motions: `pop`, `rise`, `slide_left`, `slide_right`, `drift`, `shake`.
`x` and `y` are normalized 0..1 coordinates and override a named layout.

## Vision integration contract
A vision model can inspect sampled scene frames and emit `visual_text_events`. Recommended rules:
- Keep text away from faces, products and important on-screen text.
- Prefer empty/low-detail negative space.
- Keep text inside platform safe areas.
- Move text only when it improves readability; avoid constant motion.
- Use hook/number/CTA styles sparingly.

## Subject-behind-text limitation
True text *behind* a person/object requires a segmentation or depth matte. V4 deliberately does not fake this. Supply a pre-rendered transparent overlay/matte through the existing `overlays` pipeline when subject segmentation is available.
