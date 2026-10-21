# V2 Short-form editor plan

## Implemented in this build
- `helpers/analyze_short.py`: local scene-cut detection, beat/tempo extraction, RMS audio stats, source metadata.
- `helpers/make_short_edl.py`: starter EDL generator for visual-first montages.
- `helpers/render.py`: `output.aspect` support for 9:16 / 16:9 / 1:1 / source framing.
- Existing transcript-first workflow remains unchanged.
- Existing test suite still passes.

## Recommended next modules
1. `visual_review.py`: contact sheets for every detected scene + visual quality scoring.
2. `subject_crop.py`: face/person/object-aware crop trajectory instead of fixed center crop.
3. `text_region_review.py`: identify persistent corner text/logo candidates and generate a review sheet before cleanup.
4. `music_plan.py`: select/import a user-authorized music track, beat-grid it, duck original audio, and align major cuts to strong beats.
5. `motion_fx.py`: bounded punch-in, pan, speed-ramp, freeze/hold, flash/blur transition primitives driven by EDL fields.
6. `short_qc.py`: check black frames, crop errors, subtitle safe zones, loudness, abrupt cuts and output duration.

## Proposed V2 EDL additions
```json
{
  "output": {"aspect": "9:16", "crop_mode": "center"},
  "short_form": {"target_seconds": 20, "beat_sync": true, "safe_zones": true},
  "ranges": [
    {"source": "main", "start": 1.2, "end": 3.8, "beat": "HOOK"}
  ]
}
```

Keep effects explicit in the EDL so every automated decision remains inspectable and reversible.

## V2.2 — Dynamic text / caption engine (implemented)
- Animated ASS/libass captions generated directly from word timestamps.
- Default preset is now `viral_pop` for short-form renders built with `--build-subtitles`.
- `viral_pop`: elastic pop-in + word-by-word karaoke highlight + thick readable outline.
- `punch`: stronger scale/blur entrance for hooks and high-energy edits.
- `clean`: restrained fade for commercial / real-estate / informational videos.
- `cinematic`: softer fade + tracking for emotional / scenic edits.
- `classic`: preserves the original SRT caption behavior.
- Preset can be selected with `--caption-style` or EDL field `"caption_style"`.

Examples:
```bash
python helpers/render.py edit/edl.json -o final.mp4 --build-subtitles --caption-style viral_pop
python helpers/render.py edit/edl.json -o final.mp4 --build-subtitles --caption-style punch
```

EDL:
```json
{"caption_style": "viral_pop"}
```

The ASS file remains editable/inspectable at `edit/master.ass`, so generated text effects are reversible rather than baked into opaque AI output.
