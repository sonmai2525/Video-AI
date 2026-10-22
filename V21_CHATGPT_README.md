# VIDEO AI EDITOR V21 — CHATGPT EDITION

## Important
This version is intended for a ChatGPT session that has a Python runtime and FFmpeg installed. Merely uploading a ZIP **does not** automatically execute it. The user must ask the assistant to extract the ZIP, read this file, and run the pipeline using tools available in that session. ChatGPT sessions do not necessarily offer TTS or arbitrary outbound Internet. No generic upload site is required. Video file sharing works only if the session supports generating file attachments.

## Workflow
1. Upload the ZIP and source MP4 to ChatGPT. Ask ChatGPT to extract into a working directory and inspect the source.
2. Request an accurate narration script from the actual video; save as UTF-8 `VOICE_SCRIPT.txt`. Do not invent descriptions for unseen footage.
3. If online TTS is supported, `python helpers/chatgpt_export_v21.py source.mp4 --script VOICE_SCRIPT.txt --output OUTPUT/final.mp4`. Requires `edge-tts` installed and network access to its service; the command fails if unavailable.
4. If TTS is unavailable, supply an actual MP3/WAV narration file and run `python helpers/chatgpt_export_v21.py source.mp4 --script VOICE_SCRIPT.txt --voice-file narration.mp3 --output OUTPUT/final.mp4`. Installing Edge TTS on the user's laptop will not help the ChatGPT runtime.
5. To process **user-provided regions** of a watermark, add `--logo-boxes '420,10,290,65;240,1060,300,90'`. These values are EXAMPLES for 720x1280, not automatic detection. Delogo interpolation may damage underlying content. Only edit source videos that you have the right to modify.
6. Share the OUTPUT MP4 via ChatGPT's file attachment if it supports this. Never claim a public URL has been created unless a real upload succeeded.

## Quality and truthful reporting
- Fails rather than publishes a silent result when TTS or a usable narration audio file is missing.
- Pre-validates the narration audio track, refuses narration longer than the video and probes the final audio/video streams. This cannot confirm intelligibility or subjective quality. Review by listening.
- Animated karaoke subtitles have **estimated word timings**, not forced alignment with actual speech. For professional frame-accurate subtitles, replace the estimated timings with word-alignment timestamps.
- Supports pre-edited video as input; does not automatically build story edits from arbitrary footage. Original V20 modules remain available for earlier stages.
- Source audio is mixed at low volume with narration; if there's no source audio, narration is used alone.
- No need for .bat, no tmpfiles.org, no external file host dependency.

## Quick check
`ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name -of json OUTPUT/final.mp4`

## Troubleshooting
- `AI voice generation unavailable`: provide a voice MP3 via `--voice-file`, or enable a supported online TTS connector in the actual runtime.
- `Narration exceeds video`: shorten the script or lengthen the edited video.
- `Logo box invalid`: measure boxes on the actual video resolution and keep small. To preserve artwork, leave these regions untouched or obtain clean source footage.
- Cannot download from ChatGPT: the assistant must attach an actual generated file; a link from an unsupported file-host cannot substitute.
