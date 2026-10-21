# Text Engine V3

`auto_dynamic` is now the default caption mode for short-form edits.

Instead of forcing one visual preset across the whole video, each cue can be classified as:
- `hook` — oversized snap/pop entrance for opening questions and attention words
- `emphasis` — stronger bounce for important claims
- `number` — larger numeric treatment for prices, percentages and figures
- `cta` — strong ending/action treatment
- `emotion` — softer cinematic movement
- `viral_pop` — normal word-following karaoke captions

## AI / editor overrides
An upstream agent can make semantic decisions explicitly in the EDL:

```json
{
  "caption_style": "auto_dynamic",
  "caption_events": [
    {"start": 0.0, "end": 1.4, "role": "hook"},
    {"start": 3.2, "end": 4.5, "role": "number"},
    {"start": 8.0, "end": 10.0, "role": "cta"}
  ]
}
```

This is preferred when an LLM understands the meaning of the full video. The local rules are a safe offline fallback.

## CLI

```bash
python helpers/render.py edit/edl.json -o final.mp4 --build-subtitles --caption-style auto_dynamic
```
