# V8 — Semantic Vision Director

V8 adds multi-frame visual understanding before final render. It samples every detected scene at several moments and creates a semantic scene record with: face/person cues, likely subject region, action/motion level, approximate shot scale, brightness, complexity, and a negative-space-safe caption position.

The V8 plan is written to `semantic.v8.json` and embedded into the EDL as `semantic_vision`. It also upgrades `visual_text_events` so captions avoid important regions using evidence from multiple frames rather than one midpoint frame, and enriches clips with `semantic_tags`, `subject_region`, and `action_level`.

Run the full editor as before:

```bash
python helpers/auto_viral_editor.py input.mp4 -o final.mp4 --target 20 --aspect 9:16
```

Or run V8 alone:

```bash
python helpers/semantic_vision_director.py input.mp4 edit/analysis.json -o edit/semantic.v8.json --edl edit/edl.json --apply
```

## Design boundary

The bundled local engine intentionally uses transparent computer-vision cues and does not pretend to recognize every arbitrary object or understand story meaning like a large multimodal model. Its JSON contract is designed so a multimodal provider can later enrich `semantic_tags` while downstream render/edit code stays compatible.
