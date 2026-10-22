# V20 - Voice and caption placement + two explicit logo regions

1. Install dependencies with SETUP_ONCE.bat. Internet is required for Edge TTS.
2. Put source video(s) in INPUT; run EDIT_VOICE_V20.bat.
3. For high-quality narration, create VOICE_SCRIPT.txt (UTF-8), one short sentence per line. If absent, V20 makes a generic provisional narration automatically. Always review it for accuracy.
4. Set `watermark_boxes = x,y,w,h;x,y,w,h` in V16_CONFIG.ini to designate TWO source-coordinate regions. The sample picture is approximately 720x1280. Example: `watermark_boxes = 420,10,290,65;240,1060,300,90`. You MUST check your source resolution and exact bounds. Leaving blank preserves the source. Logo patches use FFmpeg delogo interpolation and can leave visible artifacts when covering artwork; review the results.
5. Captions are placed lower in vertical videos. AI voice is REQUIRED by default. If Edge TTS is unavailable (network blocked), the render FAILS instead of reporting a voiced video when there is none. No offline TTS is bundled.
6. Output is in OUTPUT. Check the mp4 audio track and review by listening; merely having an audio track does not prove the presence of voice.

The V19 screenshot is from an external preview UI; this local editor cannot change the export pipeline of that external site.
