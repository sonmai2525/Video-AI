# V10.1 Fast Quality

Default mode is now `fast-quality`: analyze → starter EDL → visual director → light creative director → render → QC. It intentionally skips the expensive V8/V9/V10 semantic/story passes unless `--mode full-ai` is requested.

## Recommended
```bash
python helpers/auto_viral_editor.py input.mp4 -o final.mp4 --mode fast-quality --target 20 --aspect 9:16
```

## Watermark/logo cleanup
For a known logo rectangle, pass pixel coordinates:
```bash
python helpers/auto_viral_editor.py input.mp4 -o final.mp4 --mode fast-quality --watermark-box 0,0,220,70
```
V10.1 removes small edge watermarks by cropping the contaminated strip before reframing. This preserves real texture and avoids the smeared `delogo` look. If the mark is interior/too large, automatic destructive blur/inpaint is refused rather than damaging the footage. Use `--max-watermark-crop` to control the maximum sacrificed edge fraction (default 0.12).

Use `--mode full-ai` only when the source genuinely benefits from semantic/story restructuring.
