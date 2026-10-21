# V19 - Voice and animated captions

1. Copy `VOICE_SCRIPT_EXAMPLE.txt` to `VOICE_SCRIPT.txt`; edit UTF-8 Vietnamese lines (one narration sentence per line).
2. Run `EDIT_VOICE_V19.bat` (requires `SETUP_ONCE.bat`, Internet for edge-tts).
3. V19 refuses to mark an output successful if voice is requested but synthesis fails. Use direct CLI `--allow-no-voice` only when you explicitly want a silent output.
4. Animated captions are built from the supplied speech script, on the same EDL timeline. Timing is **estimated by equal division of words**, not forced alignment. The voice synthesis currently trims long sentences to allotted durations; use short lines to avoid cut-off.
5. Without a script, existing V15 plans are used if available; if empty, the editor **stops** rather than silently generating a video with no narration.
