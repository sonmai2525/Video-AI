"""Analyze a short-form video for scene cuts, beats and basic visual/audio metadata.

Produces JSON that an editing agent can use even when there is little/no speech.
No cloud API is required; ffmpeg/ffprobe are mandatory and librosa is optional.

Usage:
  python helpers/analyze_short.py input.mp4 -o edit/analysis.json
"""
from __future__ import annotations
import argparse, json, re, subprocess, tempfile, wave
from pathlib import Path
import numpy as np


def probe(video: Path) -> dict:
    cmd=["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(video)]
    data=json.loads(subprocess.check_output(cmd,text=True))
    v=next((s for s in data.get("streams",[]) if s.get("codec_type")=="video"),{})
    a=next((s for s in data.get("streams",[]) if s.get("codec_type")=="audio"),None)
    dur=float(data.get("format",{}).get("duration") or v.get("duration") or 0)
    return {"duration":dur,"width":v.get("width"),"height":v.get("height"),
            "fps":v.get("avg_frame_rate") or v.get("r_frame_rate"),
            "video_codec":v.get("codec_name"),"has_audio":bool(a),
            "audio_codec":a.get("codec_name") if a else None}


def scene_cuts(video: Path, threshold: float=.30, quick: bool=False) -> list[float]:
    # showinfo prints pts_time only for frames selected by scene score.
    filt=(f"fps=10,scale=480:-2,select='gt(scene,{threshold})',showinfo" if quick
          else f"select='gt(scene,{threshold})',showinfo")
    p=subprocess.run(["ffmpeg","-hide_banner","-i",str(video),"-vf",filt,"-an","-f","null","-"],
                     stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    vals=[]
    for m in re.finditer(r"pts_time:([0-9.]+)",p.stderr):
        t=float(m.group(1))
        if not vals or abs(t-vals[-1])>.08: vals.append(round(t,3))
    return vals


def extract_audio(video: Path, wav: Path) -> bool:
    p=subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(video),
                      "-vn","-ac","1","-ar","22050","-c:a","pcm_s16le",str(wav)])
    return p.returncode==0 and wav.exists() and wav.stat().st_size>44


def audio_analysis(video: Path) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".wav",delete=False) as f: wav=Path(f.name)
    try:
        if not extract_audio(video,wav): return {"tempo_bpm":None,"beats":[],"rms_mean":None}
        try:
            import librosa
            y,sr=librosa.load(str(wav),sr=None,mono=True)
            tempo, frames=librosa.beat.beat_track(y=y,sr=sr)
            beats=librosa.frames_to_time(frames,sr=sr)
            rms=librosa.feature.rms(y=y)[0]
            tempo=float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else None
            return {"tempo_bpm":round(tempo,2) if tempo else None,
                    "beats":[round(float(x),3) for x in beats.tolist()],
                    "rms_mean":round(float(np.mean(rms)),6) if rms.size else None}
        except Exception:
            with wave.open(str(wav),"rb") as w:
                pcm=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768.0
            return {"tempo_bpm":None,"beats":[],"rms_mean":round(float(np.sqrt(np.mean(pcm**2))),6) if pcm.size else None}
    finally: wav.unlink(missing_ok=True)


def segments_from_cuts(duration: float, cuts: list[float]) -> list[dict]:
    pts=[0.0]+[x for x in cuts if .08<x<duration-.08]+[duration]
    out=[]
    for i,(a,b) in enumerate(zip(pts,pts[1:])):
        if b-a>=.12: out.append({"id":i,"start":round(a,3),"end":round(b,3),"duration":round(b-a,3)})
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("video",type=Path); ap.add_argument("-o","--output",type=Path,required=True)
    ap.add_argument("--scene-threshold",type=float,default=.30)
    ap.add_argument("--quick",action="store_true",help="10 fps / 480p scene scan, skip audio beat extraction")
    args=ap.parse_args(); video=args.video.resolve()
    meta=probe(video); cuts=scene_cuts(video,args.scene_threshold,args.quick); audio=({"tempo_bpm":None,"beats":[],"rms_mean":None} if args.quick else audio_analysis(video))
    data={"version":2,"source":str(video),"metadata":meta,"scene_threshold":args.scene_threshold,
          "scene_cuts":cuts,"scenes":segments_from_cuts(meta["duration"],cuts),"audio":audio,
          "agent_notes":["Use scenes as visual edit units; do not assume speech exists.",
                         "Use beats as optional cut targets, not mandatory cut points.",
                         "Inspect a timeline/contact sheet before removing logos or text; static text may be intentional content."]}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print(f"wrote {args.output} | {len(data['scenes'])} scenes | {len(audio['beats'])} beats")
if __name__=="__main__": main()
