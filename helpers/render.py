"""Render a video from an EDL.

Implements the HEURISTICS render pipeline in the correct order:

  1. Per-segment extract with color grade + 30ms audio fades baked in
  2. Lossless -c copy concat into base.mp4
  3. If overlays or subtitles: single filter graph that overlays animations
     (with PTS shift so frame 0 lands at the overlay window start)
     and applies `subtitles` filter LAST → final.mp4

Optionally builds a master SRT from the per-source transcripts + EDL
output-timeline offsets, applies the proven force_style (2-word
UPPERCASE chunks, Helvetica 18 Bold, MarginV=35).

Usage:
    python helpers/render.py <edl.json> -o final.mp4
    python helpers/render.py <edl.json> -o preview.mp4 --preview
    python helpers/render.py <edl.json> -o final.mp4 --build-subtitles
    python helpers/render.py <edl.json> -o final.mp4 --no-subtitles
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

try:
    from grade import get_preset, auto_grade_for_clip  # same directory
except Exception:
    def get_preset(name: str) -> str:
        return ""

    def auto_grade_for_clip(video, start=0.0, duration=None, verbose=False):  # type: ignore
        return "eq=contrast=1.03:saturation=0.98", {}


# -------- Subtitle style (bold-overlay, proven at 1920×1080 and 1080×1920) --
#
# MarginV is NOT taste — it is a platform safe-zone rule.
# TikTok / IG Reels / Shorts UI (caption, username, music, right-rail actions)
# covers roughly the bottom ~25–30% of a 1080×1920 frame. Captions placed near
# the bottom edge get clipped or obscured by the UI. libass auto-scales the
# render canvas relative to PlayResY=288, so MarginV=90 lands the caption
# baseline roughly 30% up from the bottom on any aspect — clear of the UI on
# every major vertical-video platform. Do not drop this below ~75 without a
# specific reason.
SUB_FORCE_STYLE = (
    "FontName=Helvetica,FontSize=18,Bold=1,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H00000000,"
    "BorderStyle=1,Outline=2,Shadow=0,"
    "Alignment=2,MarginV=90"
)

# -------- Text Engine V3: semantic + animated short-form captions -----------
# The V3 engine can keep one preset for the whole video, or choose a treatment
# cue-by-cue (hook, emphasis, number, CTA, emotion, normal) in "auto_dynamic".
CAPTION_PRESETS = {
    "viral_pop": {"font":"Arial","size":62,"primary":"&H00FFFFFF","secondary":"&H0000D7FF","outline":"&H00101010","outline_w":5,"shadow":3,"margin_v":500,"transform":r"{\fscx72\fscy72\t(0,110,\fscx112\fscy112)\t(110,190,\fscx100\fscy100)}","karaoke":True},
    "punch": {"font":"Arial","size":66,"primary":"&H00FFFFFF","secondary":"&H0048A7FF","outline":"&H00000000","outline_w":6,"shadow":4,"margin_v":520,"transform":r"{\blur1\fscx55\fscy55\t(0,90,\fscx118\fscy118\blur0)\t(90,165,\fscx100\fscy100)}","karaoke":True},
    "clean": {"font":"Arial","size":56,"primary":"&H00FFFFFF","secondary":"&H00FFFFFF","outline":"&H00101010","outline_w":4,"shadow":2,"margin_v":500,"transform":r"{\fad(70,90)}","karaoke":False},
    "cinematic": {"font":"Arial","size":48,"primary":"&H00FFFFFF","secondary":"&H00FFFFFF","outline":"&H00202020","outline_w":2,"shadow":1,"margin_v":430,"transform":r"{\fsp2\fad(180,220)}","karaoke":False},
    # V3 role presets
    "hook": {"font":"Arial","size":76,"primary":"&H00FFFFFF","secondary":"&H0000D7FF","outline":"&H00000000","outline_w":7,"shadow":4,"margin_v":610,"transform":r"{\blur2\fscx45\fscy45\frz-3\t(0,90,\blur0\fscx122\fscy122\frz1)\t(90,180,\fscx100\fscy100\frz0)}","karaoke":True},
    "emphasis": {"font":"Arial","size":70,"primary":"&H00FFFFFF","secondary":"&H0000D7FF","outline":"&H00101010","outline_w":6,"shadow":4,"margin_v":520,"transform":r"{\fscx70\fscy70\t(0,100,\fscx116\fscy116)\t(100,180,\fscx100\fscy100)}","karaoke":True},
    "number": {"font":"Arial","size":78,"primary":"&H0000D7FF","secondary":"&H0000FFFF","outline":"&H00000000","outline_w":7,"shadow":4,"margin_v":560,"transform":r"{\fscx40\fscy40\t(0,120,\fscx125\fscy125)\t(120,220,\fscx100\fscy100)}","karaoke":True},
    "cta": {"font":"Arial","size":68,"primary":"&H00FFFFFF","secondary":"&H0048A7FF","outline":"&H00000000","outline_w":6,"shadow":4,"margin_v":610,"transform":r"{\fad(60,140)\fscx75\fscy75\t(0,140,\fscx108\fscy108)\t(140,230,\fscx100\fscy100)}","karaoke":True},
    "emotion": {"font":"Arial","size":54,"primary":"&H00FFFFFF","secondary":"&H00FFFFFF","outline":"&H00202020","outline_w":3,"shadow":2,"margin_v":450,"transform":r"{\fsp2\fad(160,220)\move(540,1490,540,1460,0,260)}","karaoke":False},
}

# Lightweight semantic rules. They deliberately work offline and can be
# overridden by EDL caption_events when an upstream LLM has richer context.
HOOK_WORDS = {"wait","watch","stop","look","listen","secret","why","how","đợi","xem","dừng","nhìn","bí mật","tại sao","cách"}
CTA_WORDS = {"follow","subscribe","comment","share","save","like","click","dm","theo dõi","đăng ký","bình luận","chia sẻ","lưu","nhấn"}
EMOTION_WORDS = {"amazing","beautiful","wow","love","crazy","incredible","sad","happy","đẹp","tuyệt","yêu","điên","bất ngờ","hạnh phúc","buồn"}
EMPHASIS_WORDS = {"best","never","always","must","important","biggest","only","nhất","không bao giờ","luôn","phải","quan trọng","duy nhất"}

def _ass_ts(seconds: float) -> str:
    seconds=max(0.0,seconds); h=int(seconds//3600); seconds-=h*3600; m=int(seconds//60); seconds-=m*60
    return f"{h}:{m:02d}:{seconds:05.2f}"

def _ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

def _range_speed(r: dict) -> float:
    """Playback speed for a range. 1.0 keeps source timing."""
    try:
        return max(0.25, min(4.0, float(r.get("speed", 1.0))))
    except (TypeError, ValueError):
        return 1.0

def _caption_entries(edl: dict, edit_dir: Path):
    transcripts_dir=edit_dir/"transcripts"; entries=[]; seg_offset=0.0
    for r in edl["ranges"]:
        src_name=r["source"]; seg_start=float(r["start"]); seg_end=float(r["end"]); tr_path=transcripts_dir/f"{src_name}.json"
        if tr_path.exists():
            transcript=json.loads(tr_path.read_text())
            for chunk in chunk_words(_words_in_range(transcript,seg_start,seg_end)):
                local_start=max(seg_start,chunk[0].get("start",seg_start)); local_end=min(seg_end,chunk[-1].get("end",seg_end))
                speed=_range_speed(r)
                a=max(0.0,local_start-seg_start)/speed+seg_offset; b=max(a+0.12,(local_end-seg_start)/speed+seg_offset)
                words=[(w.get("text") or "").strip().rstrip(",;:") for w in chunk]; words=[x for x in words if x]
                durations=[max(0.06,(float(w.get("end",0))-float(w.get("start",0)))/_range_speed(r)) for w in chunk]
                entries.append((a,b," ".join(words).upper(),durations))
        else: print(f"  no transcript for {src_name}, skipping captions for this segment")
        seg_offset += (seg_end-seg_start)/_range_speed(r)
    return sorted(entries,key=lambda e:e[0])

def _semantic_role(text: str, cue_index: int, cue_count: int) -> str:
    low=text.lower()
    tokens=set(re.findall(r"[^\W_]+", low, flags=re.UNICODE))
    if re.search(r"(?:^|\s)[€$£₫]?\d[\d.,]*(?:%|k|m|tr|triệu|tỷ)?(?:\s|$)", low): return "number"
    if any(x in low for x in CTA_WORDS): return "cta"
    if cue_index < 2 and (any(x in low for x in HOOK_WORDS) or "?" in text): return "hook"
    if any(x in low for x in EMPHASIS_WORDS): return "emphasis"
    if any(x in low for x in EMOTION_WORDS): return "emotion"
    if cue_index == cue_count-1 and any(x in low for x in CTA_WORDS): return "cta"
    return "viral_pop"

def _event_override(edl: dict, a: float, b: float):
    """Return role/style from optional caption_events overlapping this cue.
    Example: {"start":0,"end":1.5,"role":"hook"}.
    """
    best=None; best_overlap=0.0
    for ev in edl.get("caption_events") or []:
        ea=float(ev.get("start",0)); eb=float(ev.get("end",ea)); overlap=max(0.0,min(b,eb)-max(a,ea))
        if overlap>best_overlap:
            best_overlap=overlap; best=ev.get("style") or ev.get("role")
    return best if best in CAPTION_PRESETS else None

def _karaoke_body(text: str, durations: list[float], active_colour="&H0000D7FF") -> str:
    words=_ass_escape(text).split(); tags=[]
    for i,word in enumerate(words):
        d=durations[i] if i<len(durations) else 0.18
        # \kf fills each word over its spoken duration. SecondaryColour is the
        # active/highlight colour, so the eye follows speech instead of a block.
        tags.append(r"{\kf%d}%s"%(max(6,round(d*100)),word))
    return " ".join(tags)


# -------- Text Engine V4: visual layout + kinetic typography ----------------
# V4 adds scene-aware layout metadata without requiring a heavyweight vision
# dependency inside render.py. An upstream vision model/analyzer can populate
# visual_text_events; render.py then turns those decisions into deterministic
# ASS positioning, motion, boxes and icon accents.
V4_LAYOUTS = {
    "center": (540, 960),
    "upper": (540, 560),
    "lower_safe": (540, 1320),
    "left": (300, 900),
    "right": (780, 900),
    "top_left": (300, 500),
    "top_right": (780, 500),
}

def _visual_event(edl: dict, a: float, b: float) -> dict:
    best={}; best_overlap=0.0
    for ev in (edl.get("visual_text_events") or []) + (edl.get("v15_text_cards") or []):
        ea=float(ev.get("start",0)); eb=float(ev.get("end",ea))
        overlap=max(0.0,min(b,eb)-max(a,ea))
        if overlap>best_overlap:
            best_overlap=overlap; best=ev
    return best

def _v4_layout_tag(ev: dict, idx: int) -> str:
    layout=ev.get("layout") or "center"
    x,y=V4_LAYOUTS.get(layout,V4_LAYOUTS["center"])
    # Explicit normalized coordinates are useful when vision knows the subject.
    if "x" in ev: x=max(70,min(1010,round(float(ev["x"])*1080)))
    if "y" in ev: y=max(120,min(1740,round(float(ev["y"])*1920)))
    motion=ev.get("motion") or "pop"
    if motion=="slide_left": return rf"{{\move({x-150},{y},{x},{y},0,220)}}"
    if motion=="slide_right": return rf"{{\move({x+150},{y},{x},{y},0,220)}}"
    if motion=="rise": return rf"{{\move({x},{y+90},{x},{y},0,240)}}"
    if motion=="drift": return rf"{{\move({x-30},{y+25},{x+30},{y-15},0,700)}}"
    if motion=="shake": return rf"{{\pos({x},{y})\frz-2\t(0,70,\frz2)\t(70,140,\frz-1)\t(140,210,\frz0)}}"
    return rf"{{\pos({x},{y})}}"

def _v4_decorate(text: str, ev: dict) -> str:
    # Keep icons deliberately simple/Unicode so the project stays dependency-free.
    icon=str(ev.get("icon") or "").strip()
    if icon and len(icon)<=4: text=f"{icon} {text}"
    return text

def _v4_box_tag(ev: dict) -> str:
    # ASS opaque-box mode. BorderStyle=3 is applied inline only when requested.
    if not ev.get("box"): return ""
    opacity=str(ev.get("box_opacity","88"))
    return rf"{{\bord0\shad0\3c&H000000&\3a&H{opacity}&}}"

def build_master_ass_v4(edl: dict, edit_dir: Path, out_path: Path, preset_name: str="auto_dynamic") -> None:
    """V4 caption renderer: V3 semantics + per-scene position/motion/decor.

    visual_text_events example:
      {"start":0,"end":1.2,"layout":"upper","motion":"rise","icon":"🔥",
       "box":true,"style":"hook"}
    Coordinates x/y may be supplied normalized 0..1 by a vision analyzer.
    """
    auto=preset_name in {"auto_dynamic","visual_dynamic"}
    entries=_caption_entries(edl,edit_dir)
    # V15 motion-typography cards can exist even when the source has no useful transcript.
    for card in edl.get("v15_text_cards") or []:
        a=float(card.get("start",0)); b=max(a+.2,float(card.get("end",a+.8))); text=str(card.get("text","")).strip()
        if text: entries.append((a,b,text,[max(.08,(b-a)/max(1,len(text.split())))]*max(1,len(text.split()))))
    entries.sort(key=lambda x:x[0])
    header=("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n"
            "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n")
    lines=[header]
    for name,p in CAPTION_PRESETS.items():
        lines.append(f"Style: {name},{p['font']},{p['size']},{p['primary']},{p['secondary']},{p['outline']},&H64000000,-1,0,0,0,100,100,0,0,1,{p['outline_w']},{p['shadow']},5,40,40,40,1\n")
    lines.append("\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
    for idx,(a,b,text,durations) in enumerate(entries):
        ev=_visual_event(edl,a,b)
        style=ev.get("style") if ev.get("style") in CAPTION_PRESETS else ((_event_override(edl,a,b) or _semantic_role(text,idx,len(entries))) if auto else preset_name)
        if style not in CAPTION_PRESETS: style="viral_pop"
        p=CAPTION_PRESETS[style]
        text=_v4_decorate(text,ev)
        body=_karaoke_body(text,durations,p["secondary"]) if p["karaoke"] else _ass_escape(text)
        body=_v4_layout_tag(ev,idx)+_v4_box_tag(ev)+p["transform"]+body
        lines.append(f"Dialogue: 0,{_ass_ts(a)},{_ass_ts(b)},{style},v4-{style},0,0,0,,{body}\n")
    out_path.write_text("".join(lines))
    print(f"master ASS → {out_path.name} (V4 {preset_name}, {len(entries)} cues)")

def build_master_ass(edl: dict, edit_dir: Path, out_path: Path, preset_name: str="viral_pop") -> None:
    auto = preset_name == "auto_dynamic"
    if not auto and preset_name not in CAPTION_PRESETS: raise ValueError(f"unknown caption preset: {preset_name}")
    entries=_caption_entries(edl,edit_dir)
    # Multiple named styles let one video switch visual language cue-by-cue.
    header=("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n"
            "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n")
    lines=[header]
    for name,p in CAPTION_PRESETS.items():
        lines.append(f"Style: {name},{p['font']},{p['size']},{p['primary']},{p['secondary']},{p['outline']},&H64000000,-1,0,0,0,100,100,0,0,1,{p['outline_w']},{p['shadow']},2,70,70,{p['margin_v']},1\n")
    lines.append("\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
    for idx,(a,b,text,durations) in enumerate(entries):
        style = (_event_override(edl,a,b) or _semantic_role(text,idx,len(entries))) if auto else preset_name
        p=CAPTION_PRESETS[style]
        body=_karaoke_body(text,durations,p["secondary"]) if p["karaoke"] else _ass_escape(text)
        body=p["transform"]+body
        # Role is kept in Name for easy inspection/debugging of generated ASS.
        lines.append(f"Dialogue: 0,{_ass_ts(a)},{_ass_ts(b)},{style},{style},0,0,0,,{body}\n")
    out_path.write_text("".join(lines)); print(f"master ASS → {out_path.name} ({preset_name}, {len(entries)} cues)")

# -------- Helpers ------------------------------------------------------------


def run(cmd: list[str], quiet: bool = False) -> None:
    if not quiet:
        print(f"  $ {' '.join(str(c) for c in cmd[:6])}{' …' if len(cmd) > 6 else ''}")
    subprocess.run(cmd, check=True)


def resolve_grade_filter(grade_field: str | None) -> str:
    """The EDL's 'grade' field can be a preset name, a raw ffmpeg filter, or 'auto'.

    Returns the filter string to embed into the per-segment -vf chain.
    For 'auto', returns the sentinel "__AUTO__" which is resolved per-segment.
    """
    if not grade_field:
        return ""
    if grade_field == "auto":
        return "__AUTO__"
    # Preset names are short identifiers, filter strings contain '=' or ','.
    if re.fullmatch(r"[a-zA-Z0-9_\-]+", grade_field):
        try:
            return get_preset(grade_field)
        except KeyError:
            print(f"warning: unknown preset '{grade_field}', using as raw filter")
            return grade_field
    return grade_field


def resolve_path(maybe_path: str, base: Path) -> Path:
    """Resolve a path that may be absolute or relative to `base`."""
    p = Path(maybe_path)
    if p.is_absolute():
        return p
    return (base / p).resolve()


def resolve_subtitles_path(maybe_path: str, edit_dir: Path) -> Path:
    """Resolve the EDL's subtitles path: relative to the EDL's directory, else the
    current directory (agents often write "edit/master.srt"). A missing file is an
    error: rendering on without it silently ships a video with no captions."""
    candidates = [resolve_path(maybe_path, edit_dir)]
    if not Path(maybe_path).is_absolute():
        candidates.append(Path(maybe_path).resolve())
    for c in candidates:
        if c.exists():
            return c
    tried = ", ".join(str(c) for c in candidates)
    sys.exit(f"subtitles file in EDL not found (tried {tried}). Fix the path or pass --no-subtitles.")


# -------- HDR → SDR tone mapping (HLG / PQ sources) --------------------------
#
# iPhone defaults to HLG HDR in Rec.2020 (and many mirrorless cameras ship PQ).
# If the source is HDR and we only downconvert bit depth (yuv420p10le → yuv420p)
# without tone-mapping, the output is 8-bit but still carries HLG/PQ transfer
# metadata. Players that honor the metadata (screen recorders, most social
# upload re-encodes) interpret 8-bit values in an HDR container and the result
# looks oversaturated / blown out. QuickTime on macOS can hide this locally —
# screen recording and uploaded renders cannot.
#
# Fix: detect HDR via color_transfer and prepend a zscale+tonemap chain to the
# vf graph so the output is clean Rec.709 SDR.

HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}  # PQ (HDR10) and HLG

TONEMAP_CHAIN = (
    "zscale=t=linear:npl=100,"
    "format=gbrpf32le,"
    "zscale=p=bt709,"
    "tonemap=tonemap=hable:desat=0,"
    "zscale=t=bt709:m=bt709:r=tv,"
    "format=yuv420p"
)


def is_hdr_source(video: Path) -> bool:
    """Return True if the source uses a PQ or HLG transfer function."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=color_transfer",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip() in HDR_TRANSFERS
    except subprocess.CalledProcessError:
        return False


def is_portrait_source(video: Path) -> bool:
    """Return True if the displayed video is portrait, including rotation."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries",
             "stream=width,height:stream_side_data=rotation",
             "-of", "json", str(video)],
            capture_output=True, text=True, check=True,
        )
        streams = json.loads(out.stdout).get("streams") or []
        if not streams:
            return False
        stream = streams[0]
        w, h = int(stream["width"]), int(stream["height"])

        # ffmpeg autorotates display-matrix side data before applying filters.
        # Swap coded dimensions for quarter-turns so the scale axis is selected
        # from the dimensions the filter actually sees. A plain metadata tag is
        # intentionally ignored because it does not guarantee autorotation.
        rotation = 0
        for side_data in stream.get("side_data_list") or []:
            if side_data.get("rotation") is not None:
                rotation = side_data["rotation"]
                break
        if int(round(float(rotation))) % 360 in (90, 270):
            w, h = h, w
        return h > w
    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        OSError,
        OverflowError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return False


def parse_fps(value: str) -> str:
    """Validate and canonicalize an ffmpeg frame rate."""
    text = value.strip()
    if len(text) > 32 or not re.fullmatch(
        r"(?:[0-9]+(?:\.[0-9]+)?|[0-9]+/[0-9]+)", text
    ):
        raise argparse.ArgumentTypeError(
            "FPS must be a positive number or rational, e.g. 30 or 30000/1001"
        )
    try:
        rate = Fraction(text)
    except (ValueError, ZeroDivisionError) as exc:
        raise argparse.ArgumentTypeError(
            "FPS must be a positive number or rational, e.g. 30 or 30000/1001"
        ) from exc
    if rate <= 0:
        raise argparse.ArgumentTypeError("FPS must be greater than zero")
    # FFmpeg stores video rates as AVRational (signed 32-bit components).
    # Bounding the reduced fraction keeps every accepted canonical value safe
    # for ffmpeg and makes parse_fps(parse_fps(value)) idempotent.
    max_component = 2_147_483_647
    if rate.numerator > max_component or rate.denominator > max_component:
        raise argparse.ArgumentTypeError("FPS precision or magnitude is too large")
    return f"{rate.numerator}/{rate.denominator}"


def probe_source_fps(video: Path) -> str | None:
    """Return an ffmpeg-ready source rate, preferring the average frame rate.

    ``avg_frame_rate`` represents the observed average and is the better default
    for variable-frame-rate inputs. ``r_frame_rate`` remains a fallback for
    streams where the average is unavailable. Values are normalized to an exact
    rational so rates such as ``30000/1001`` survive without rounding.
    """
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=avg_frame_rate,r_frame_rate",
             "-of", "json", str(video)],
            capture_output=True, text=True, check=True,
        )
        streams = json.loads(out.stdout).get("streams") or []
        if not streams:
            return None
        for field in ("avg_frame_rate", "r_frame_rate"):
            value = streams[0].get(field)
            if value and value != "0/0":
                try:
                    return parse_fps(value)
                except argparse.ArgumentTypeError:
                    continue
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError):
        return None
    return None


# -------- Per-segment extraction (Rule 2 + Rule 3) --------------------------


def extract_segment(
    source: Path,
    seg_start: float,
    duration: float,
    grade_filter: str,
    out_path: Path,
    preview: bool = False,
    draft: bool = False,
    rate: str | None = None,
    output_aspect: str = "source",
    speed: float = 1.0,
    motion: str | None = None,
    focus_x: float = 0.5,
    focus_y: float = 0.5,
) -> None:
    """Extract a cut range as its own MP4 with grade + 30ms audio fades baked in.

    `-ss` before `-i` for fast accurate seeking. Scale to 1080p from 4K.
    Portrait sources (height > width) are scaled by height to preserve orientation.

    Quality ladder:
      - final (default): 1080p libx264 fast CRF 20
      - preview:         1080p libx264 medium CRF 22 (evaluable for QC)
      - draft:           720p libx264 ultrafast CRF 28 (cut-point check only)
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    portrait = is_portrait_source(source)
    if draft:
        scale = "scale=-2:1280" if portrait else "scale=1280:-2"
    else:
        scale = "scale=-2:1920" if portrait else "scale=1920:-2"

    vf_parts: list[str] = []
    if is_hdr_source(source):
        vf_parts.append(TONEMAP_CHAIN)
    vf_parts.append(scale)
    # V2 short-form framing. Center crop is deterministic and safe; an agent can
    # later replace it with subject-aware crop coordinates after visual review.
    if output_aspect != "source":
        target = {"9:16": (9, 16), "16:9": (16, 9), "1:1": (1, 1)}.get(output_aspect)
        if target:
            aw, ah = target
            fx=max(0.0,min(1.0,float(focus_x if focus_x is not None else .5)))
            fy=max(0.0,min(1.0,float(focus_y if focus_y is not None else .5)))
            cw=f"if(gt(iw/ih,{aw}/{ah}),ih*{aw}/{ah},iw)"
            ch=f"if(gt(iw/ih,{aw}/{ah}),ih,iw*{ah}/{aw})"
            # V9 smart reframe: place the crop window around the likely subject,
            # clamped to the source frame. Center crop remains the default.
            cx=f"max(0,min(iw-({cw}),{fx:.6f}*iw-({cw})/2))"
            cy=f"max(0,min(ih-({ch}),{fy:.6f}*ih-({ch})/2))"
            vf_parts.append(f"crop='{cw}':'{ch}':'{cx}':'{cy}'")
            dims={"9:16":"1080:1920","16:9":"1920:1080","1:1":"1080:1080"}
            vf_parts.append(f"scale={dims.get(output_aspect,'1080:1920')}")
    if grade_filter:
        vf_parts.append(grade_filter)
    # V6 creative motion. Keep it deterministic and subtle: a Ken-Burns style
    # zoom can add energy to otherwise static shots without needing tracking.
    motion = motion or "none"
    if motion in {"zoom_in", "zoom_out", "punch_in", "push_out"} and output_aspect == "9:16":
        if motion == "punch_in": z = "min(zoom+0.0024,1.14)"
        elif motion == "push_out": z = "if(eq(on,1),1.12,max(1.0,zoom-0.0018))"
        elif motion == "zoom_in": z = "min(zoom+0.0008,1.08)"
        else: z = "if(eq(on,1),1.08,max(1.0,zoom-0.0008))"
        vf_parts.append(f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={rate or 24}")
    speed=max(0.25,min(4.0,float(speed or 1.0)))
    if abs(speed-1.0)>0.001:
        vf_parts.append(f"setpts=PTS/{speed:.6f}")
    vf = ",".join(vf_parts)

    # 30ms audio fades at both edges (Rule 3) — prevent pops
    rendered_duration=duration/speed
    fade_out_start = max(0.0, rendered_duration - 0.03)
    af_parts=[]
    if abs(speed-1.0)>0.001:
        # atempo supports 0.5..2 per stage; decompose wider V6 values safely.
        rem=speed
        while rem>2.0: af_parts.append("atempo=2.0"); rem/=2.0
        while rem<0.5: af_parts.append("atempo=0.5"); rem/=0.5
        af_parts.append(f"atempo={rem:.6f}")
    af_parts += ["afade=t=in:st=0:d=0.03", f"afade=t=out:st={fade_out_start:.3f}:d=0.03"]
    af=",".join(af_parts)

    if draft:
        preset, crf = "ultrafast", "28"
    elif preview:
        preset, crf = "medium", "22"
    else:
        preset, crf = "fast", "20"

    # Frame rate: use the rate the caller resolved once for the whole render
    # (every segment must share it — concat -c copy in Rule 2 requires a uniform
    # frame rate). When called standalone with no rate, preserve this source's
    # own rate; fall back to 24 only if it can't be probed.
    out_rate = rate if rate is not None else (probe_source_fps(source) or "24")

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{seg_start:.3f}",
        "-i", str(source),
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-af", af,
        "-c:v", "libx264", "-preset", preset, "-crf", crf,
        "-pix_fmt", "yuv420p", "-r", out_rate,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def extract_all_segments(
    edl: dict,
    edit_dir: Path,
    preview: bool,
    draft: bool = False,
    fps: str | None = None,
) -> list[Path]:
    """Extract every EDL range into edit_dir/clips_graded/seg_NN.mp4.
    Returns the ordered list of segment paths.

    If the EDL `grade` is "auto", analyze each segment range with
    `auto_grade_for_clip` and apply a per-segment subtle correction.
    Otherwise, apply the same preset/raw filter to every segment.
    """
    resolved = resolve_grade_filter(edl.get("grade"))
    is_auto = resolved == "__AUTO__"
    clips_dir = edit_dir / (
        "clips_draft" if draft else ("clips_preview" if preview else "clips_graded")
    )
    clips_dir.mkdir(parents=True, exist_ok=True)

    ranges = edl["ranges"]
    sources = edl["sources"]

    # Resolve ONE output frame rate for the entire render and apply it to every
    # segment. The lossless concat (Rule 2, `-c copy`) requires all segments to
    # share a frame rate; probing per-segment would diverge for multi-source
    # EDLs that mix rates (e.g. a 30fps and a 60fps source) and break the concat.
    # Explicit --fps wins; otherwise preserve the first source's rate.
    if fps is not None:
        out_rate = parse_fps(str(fps))
    elif ranges:
        first_src = resolve_path(sources[ranges[0]["source"]], edit_dir)
        out_rate = probe_source_fps(first_src) or "24"
    else:
        out_rate = "24"

    seg_paths: list[Path] = []
    print(f"extracting {len(ranges)} segment(s) → {clips_dir.name}/  @ {out_rate} fps"
          f"{' (forced)' if fps is not None else ' (from source)'}")
    if is_auto:
        print("  (auto-grade per segment: analyzing each range)")
    for i, r in enumerate(ranges):
        src_name = r["source"]
        src_path = resolve_path(sources[src_name], edit_dir)
        start = float(r["start"])
        end = float(r["end"])
        duration = end - start
        out_path = clips_dir / f"seg_{i:02d}_{src_name}.mp4"

        if is_auto:
            seg_filter, _stats = auto_grade_for_clip(src_path, start=start, duration=duration, verbose=False)
        else:
            seg_filter = resolved

        note = r.get("beat") or r.get("note") or ""
        print(f"  [{i:02d}] {src_name}  {start:7.2f}-{end:7.2f}  ({duration:5.2f}s)  {note}")
        if is_auto:
            print(f"        grade: {seg_filter or '(none)'}")
        output_aspect = (edl.get("output") or {}).get("aspect", "source")
        extract_segment(src_path, start, duration, seg_filter, out_path, preview=preview, draft=draft, rate=out_rate, output_aspect=output_aspect, speed=_range_speed(r), motion=r.get("motion"), focus_x=r.get("focus_x",.5), focus_y=r.get("focus_y",.5))
        seg_paths.append(out_path)

    return seg_paths


# -------- Lossless concat ----------------------------------------------------


def concat_segments(segment_paths: list[Path], out_path: Path, edit_dir: Path) -> None:
    """Lossless concat via the concat demuxer. No re-encode."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    concat_list = edit_dir / "_concat.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in segment_paths))

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ]
    print(f"concat → {out_path.name}")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    concat_list.unlink(missing_ok=True)


# -------- Master SRT (Rule 5) ------------------------------------------------


PUNCT_BREAK = set(".,!?;:")


def _srt_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    h, rem = divmod(total_ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _words_in_range(transcript: dict, t_start: float, t_end: float) -> list[dict]:
    out: list[dict] = []
    for w in transcript.get("words", []):
        if w.get("type") != "word":
            continue
        ws = w.get("start")
        we = w.get("end")
        if ws is None or we is None:
            continue
        if we <= t_start or ws >= t_end:
            continue
        out.append(w)
    return out


CHUNK_WORDS = 2         # target words per cue
CHUNK_MAX_WORDS = 3     # a too-short chunk may grow to this many words
CHUNK_MIN_S = 0.35      # a cue shorter than this reads as a flash
CHUNK_PAUSE_S = 0.3     # a gap this long between words ends the cue


def chunk_words(words: list[dict]) -> list[list[dict]]:
    """Group transcript words into caption cues.

    A cue closes on trailing punctuation or on a pause before the next word.
    Otherwise it closes at CHUNK_WORDS words, unless it would be on screen for
    less than CHUNK_MIN_S; then it takes up to CHUNK_MAX_WORDS words. So
    "does | is" across a pause stays split, and fast "what a" does not flash.
    """
    words = [w for w in words if (w.get("text") or "").strip()]
    chunks: list[list[dict]] = []
    current: list[dict] = []
    for i, w in enumerate(words):
        current.append(w)
        text = w["text"].strip()
        nxt = words[i + 1] if i + 1 < len(words) else None
        gap = (nxt["start"] - w["end"]) if nxt else 0.0
        dur = w["end"] - current[0]["start"]
        if (
            nxt is None
            or text[-1] in PUNCT_BREAK
            or gap >= CHUNK_PAUSE_S
            or len(current) >= CHUNK_MAX_WORDS
            or (len(current) >= CHUNK_WORDS and dur >= CHUNK_MIN_S)
        ):
            chunks.append(current)
            current = []
    return chunks


def build_master_srt(edl: dict, edit_dir: Path, out_path: Path) -> None:
    """Build an output-timeline SRT from per-source transcripts.

    - phrase-aware ~2-word chunks (see chunk_words)
    - UPPERCASE text
    - Output times computed as word.start - segment_start + segment_offset
    """
    transcripts_dir = edit_dir / "transcripts"
    sources = edl["sources"]

    entries: list[tuple[float, float, str]] = []
    seg_offset = 0.0

    for r in edl["ranges"]:
        src_name = r["source"]
        seg_start = float(r["start"])
        seg_end = float(r["end"])
        seg_duration = seg_end - seg_start

        tr_path = transcripts_dir / f"{src_name}.json"
        if not tr_path.exists():
            print(f"  no transcript for {src_name}, skipping captions for this segment")
            seg_offset += seg_duration
            continue

        transcript = json.loads(tr_path.read_text())
        words_in_seg = _words_in_range(transcript, seg_start, seg_end)

        for chunk in chunk_words(words_in_seg):
            local_start = max(seg_start, chunk[0].get("start", seg_start))
            local_end = min(seg_end, chunk[-1].get("end", seg_end))
            out_start = max(0.0, local_start - seg_start) + seg_offset
            out_end = max(0.0, local_end - seg_start) + seg_offset
            if out_end <= out_start:
                out_end = out_start + 0.4
            text = " ".join((w.get("text") or "").strip() for w in chunk)
            text = re.sub(r"\s+", " ", text).strip()
            # Strip trailing punctuation for cleaner uppercase look
            text = text.rstrip(",;:")
            text = text.upper()
            entries.append((out_start, out_end, text))

        seg_offset += seg_duration

    # Sort and write as SRT
    entries.sort(key=lambda e: e[0])
    lines: list[str] = []
    for i, (a, b, t) in enumerate(entries, start=1):
        lines.append(str(i))
        lines.append(f"{_srt_timestamp(a)} --> {_srt_timestamp(b)}")
        lines.append(t)
        lines.append("")
    out_path.write_text("\n".join(lines))
    print(f"master SRT → {out_path.name} ({len(entries)} cues)")


# -------- Loudness normalization (social-ready audio) -----------------------


# Social-media standard: -14 LUFS integrated, -1 dBTP peak, LRA 11 LU.
# Matches YouTube / Instagram / TikTok / X / LinkedIn normalization targets.
LOUDNORM_I = -14.0
LOUDNORM_TP = -1.0
LOUDNORM_LRA = 11.0


def measure_loudness(video_path: Path) -> dict[str, str] | None:
    """Run ffmpeg loudnorm first pass and parse the JSON measurement.

    Returns a dict with measured_i, measured_tp, measured_lra, measured_thresh,
    target_offset, or None if measurement failed.
    """
    filter_str = (
        f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}:print_format=json"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-nostats",
        "-i", str(video_path),
        "-af", filter_str,
        "-vn", "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # loudnorm prints the JSON to stderr at the end of the run
    stderr = proc.stderr

    # Find the JSON block — loudnorm output contains a `{ ... }` block
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(stderr[start : end + 1])
    except json.JSONDecodeError:
        return None
    needed = {"input_i", "input_tp", "input_lra", "input_thresh", "target_offset"}
    if not needed.issubset(data.keys()):
        return None
    return data


def apply_loudnorm_two_pass(
    input_path: Path,
    output_path: Path,
    preview: bool = False,
) -> bool:
    """Run two-pass loudnorm on input_path, write normalized copy to output_path.

    Returns True on success, False if measurement failed (caller should fall
    back to copying the input unchanged).

    In preview mode, skips the measurement pass and uses a one-pass approximation
    for speed. Final mode always does the proper two-pass.
    """
    if preview:
        # One-pass approximation — faster, slightly less accurate.
        filter_str = f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}"
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-nostats",
            "-i", str(input_path),
            "-c:v", "copy",
            "-af", filter_str,
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart",
            str(output_path),
        ]
        print(f"  loudnorm (1-pass preview) → {output_path.name}")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True

    # Full two-pass
    print(f"  loudnorm pass 1: measuring {input_path.name}")
    measurement = measure_loudness(input_path)
    if measurement is None:
        print("  loudnorm measurement failed — falling back to 1-pass")
        return apply_loudnorm_two_pass(input_path, output_path, preview=True)

    print(f"    measured: I={measurement['input_i']} LUFS  "
          f"TP={measurement['input_tp']}  LRA={measurement['input_lra']}")

    filter_str = (
        f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}"
        f":measured_I={measurement['input_i']}"
        f":measured_TP={measurement['input_tp']}"
        f":measured_LRA={measurement['input_lra']}"
        f":measured_thresh={measurement['input_thresh']}"
        f":offset={measurement['target_offset']}"
        f":linear=true"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-nostats",
        "-i", str(input_path),
        "-c:v", "copy",
        "-af", filter_str,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(output_path),
    ]
    print(f"  loudnorm pass 2: normalizing → {output_path.name}")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return True


# -------- Final compositing (Rule 1 + Rule 4) -------------------------------


def build_final_composite(
    base_path: Path,
    overlays: list[dict],
    subtitles_path: Path | None,
    out_path: Path,
    edit_dir: Path,
) -> None:
    """Final pass: base → overlays (PTS-shifted) → subtitles LAST → out.

    If there are no overlays and no subtitles, just copy base to out.
    """
    has_overlays = bool(overlays)
    has_subs = subtitles_path is not None and subtitles_path.exists()

    if not has_overlays and not has_subs:
        # Nothing to do — just rename/copy base to final name
        run(["ffmpeg", "-y", "-i", str(base_path), "-c", "copy", str(out_path)], quiet=True)
        return

    inputs: list[str] = ["-i", str(base_path)]
    for ov in overlays:
        ov_path = resolve_path(ov["file"], edit_dir)
        inputs += ["-i", str(ov_path)]

    filter_parts: list[str] = []
    # PTS-shift every overlay so its frame 0 lands at start_in_output
    for idx, ov in enumerate(overlays, start=1):
        t = float(ov["start_in_output"])
        filter_parts.append(f"[{idx}:v]setpts=PTS-STARTPTS+{t}/TB[a{idx}]")

    # Chain overlays on top of base
    current = "[0:v]"
    for idx, ov in enumerate(overlays, start=1):
        t = float(ov["start_in_output"])
        dur = float(ov["duration"])
        end = t + dur
        next_label = f"[v{idx}]"
        filter_parts.append(
            f"{current}[a{idx}]overlay=enable='between(t,{t:.3f},{end:.3f})'{next_label}"
        )
        current = next_label

    # Subtitles LAST — Rule 1
    if has_subs:
        subs_abs = str(subtitles_path.resolve()).replace(":", r"\:").replace("'", r"\'")
        filter_parts.append(
            (f"{current}subtitles='{subs_abs}'[outv]" if subtitles_path.suffix.lower() == '.ass' else f"{current}subtitles='{subs_abs}':force_style='{SUB_FORCE_STYLE}'[outv]")
        )
        out_label = "[outv]"
    else:
        # Rename the last overlay output to [outv] for consistency
        if has_overlays:
            filter_parts.append(f"{current}null[outv]")
            out_label = "[outv]"
        else:
            out_label = "[0:v]"

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", out_label,
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ]
    print(f"compositing → {out_path.name}")
    print(f"  overlays: {len(overlays)}, subtitles: {'yes' if has_subs else 'no'}")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


# -------- Main ---------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a video from an EDL")
    ap.add_argument("edl", type=Path, help="Path to edl.json")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output video path")
    ap.add_argument(
        "--preview",
        action="store_true",
        help="Preview mode: 1080p, medium, CRF 22 — evaluable for QC, faster than final.",
    )
    ap.add_argument(
        "--draft",
        action="store_true",
        help="Draft mode: 720p, ultrafast, CRF 28 — cut-point verification only.",
    )
    ap.add_argument(
        "--build-subtitles",
        action="store_true",
        help="Build captions from transcripts + EDL offsets before compositing",
    )
    ap.add_argument(
        "--caption-style", choices=["classic", "auto_dynamic", "visual_dynamic", *CAPTION_PRESETS.keys()], default=None,
        help="Caption look. visual_dynamic adds V4 scene-aware position/motion on top of semantic styles.",
    )
    ap.add_argument(
        "--no-subtitles",
        action="store_true",
        help="Skip subtitles even if the EDL references one",
    )
    ap.add_argument(
        "--no-loudnorm",
        action="store_true",
        help="Skip audio loudness normalization. Default is on (-14 LUFS, -1 dBTP, LRA 11).",
    )
    ap.add_argument(
        "--fps",
        type=parse_fps,
        default=None,
        help="Output frame rate. Default: preserve the source's frame rate "
             "(falls back to 24 if it can't be probed). Pass e.g. --fps 30 or "
             "--fps 30000/1001 to force.",
    )
    args = ap.parse_args()

    edl_path = args.edl.resolve()
    if not edl_path.exists():
        sys.exit(f"edl not found: {edl_path}")

    edl = json.loads(edl_path.read_text())
    edit_dir = edl_path.parent
    out_path = args.output.resolve()

    # 1. Extract per-segment (auto-grade per range if EDL grade is "auto")
    segment_paths = extract_all_segments(
        edl, edit_dir, preview=args.preview, draft=args.draft, fps=args.fps
    )

    # 2. Concat → base
    if args.draft:
        base_name = "base_draft.mp4"
    elif args.preview:
        base_name = "base_preview.mp4"
    else:
        base_name = "base.mp4"
    base_path = edit_dir / base_name
    concat_segments(segment_paths, base_path, edit_dir)

    # 3. Subtitles: build if requested, resolve final path
    subs_path: Path | None = None
    if not args.no_subtitles:
        if args.build_subtitles:
            caption_style = args.caption_style or edl.get("caption_style") or "visual_dynamic"
            if caption_style == "classic":
                subs_path = edit_dir / "master.srt"
                build_master_srt(edl, edit_dir, subs_path)
            else:
                subs_path = edit_dir / "master.ass"
                if caption_style == "visual_dynamic":
                    build_master_ass_v4(edl, edit_dir, subs_path, caption_style)
                else:
                    build_master_ass(edl, edit_dir, subs_path, caption_style)
        elif edl.get("subtitles"):
            subs_path = resolve_subtitles_path(edl["subtitles"], edit_dir)

    # 4. Composite (overlays + subtitles LAST) → intermediate (pre-loudnorm) path
    overlays = edl.get("overlays") or []
    if args.no_loudnorm:
        # Composite directly to final output
        build_final_composite(base_path, overlays, subs_path, out_path, edit_dir)
    else:
        # Composite to a temp file, then run loudnorm → final output
        tmp_composite = out_path.with_suffix(".prenorm.mp4")
        build_final_composite(base_path, overlays, subs_path, tmp_composite, edit_dir)
        print("loudness normalization → social-ready (-14 LUFS / -1 dBTP / LRA 11)")
        apply_loudnorm_two_pass(tmp_composite, out_path, preview=args.draft)
        tmp_composite.unlink(missing_ok=True)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\ndone: {out_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
