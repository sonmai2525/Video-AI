# V16 Speed Optimization

## Confirmed redundant work
- V14 voice_director wrote a JSON and SRT report but V16 narration only reads `voice_plan_v15`; that subprocess is removed from the pipeline.
- The earlier `fast` mode still executed V12 + V13 + V13.1 + V14 + V15. `turbo` skips V13/V13.1/V14 entirely, retaining V5/V6/V12/V15.
- Full-resolution, full-frame scene change detection and audio WAV/librosa analysis were expensive. Turbo scans resized 480p video at 10 fps and skips beat extraction. Scene cuts may be less accurate and beat-aligned edits unavailable.
- One rendering pass remains the default. QC repair still triggers an extra render only on an actual failure; Turbo threshold is 70 rather than 74.

## Modes
- `EDIT_TURBO.bat` quickest; suitable for rapid batch shorts, some creative/scene fidelity sacrificed.
- `EDIT_FAST.bat` balanced existing processing; full scan retained.
- `EDIT_VIDEO.bat` smart default unchanged.
- `EDIT_MAX_AI.bat` deeper analysis retained.

## Notes
- Source-video watermark cleanup (if configured), first render, output QC and optional voice mix are retained.
- TTS calls remain the most significant latency if narration is enabled; they were not removed.
- No performance speed-up percentage claimed: timings depend on hardware and source content.
