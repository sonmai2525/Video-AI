# VIDEO AI EDITOR V16 — stability & audio handoff

V16 preserves V15's creative/story pipeline and mode choices (fast/smart/max), prioritizing reliable Windows operation and valid video output.

## Fixed / improved
- New `helpers/voice_renderer_v16.py` handles silent source video by generating a silent audio bed before voice mixing.
- Speech events validated, chronologically sorted, capped at source duration and shortened before subsequent lines; malformed events skipped.
- Speech clips resampled to common stereo 48 kHz before mixing, with bounded fade-out and limiting.
- Source audio ducked under voiced windows; no-voice exports require no TTS/API calls.
- Voice outputs written to temporary filename and atomically moved into place after successful FFmpeg processing.
- Repaired edit pass now passes its **selected repaired EDL** to voice synthesis rather than always the first-pass timeline.
- `INPUT` and `OUTPUT` folders bundled; one-click runner also creates INPUT when missing.
- Four Windows launchers now check for FFmpeg/FFprobe and preserve nonzero exit codes.
- V16 work dirs and manifests prevent mislabeling as V15.
- Added regression tests for event validation and silent input.

## Verification
59 pytest tests + 15 parameterized subtests passed locally. FFmpeg voice mixing with synthetic speech was tested on a silent-source MP4. A full real-world editing run (external media, Edge TTS connectivity and all optional AI calls) was **not** verified in this environment.

## Limitations
- TTS requires network connectivity. If unavailable, main pipeline falls back to edit without narration.
- The AI/creative heuristics are not a guarantee of viral performance.
- Captions and image/crop decisions still depend on source quality.
