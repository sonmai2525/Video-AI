"""Create a conservative starter EDL from analyze_short.py output.
The result is intentionally a first pass for an agent/person to review.
Usage: python helpers/make_short_edl.py edit/analysis.json -o edit/edl.short.json --target 20
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("analysis",type=Path); ap.add_argument("-o","--output",type=Path,required=True)
    ap.add_argument("--target",type=float,default=20.0); ap.add_argument("--aspect",default="9:16",choices=["9:16","16:9","1:1","source"])
    args=ap.parse_args(); d=json.loads(args.analysis.read_text()); scenes=d.get("scenes",[])
    # Prefer complete scenes, but cap long shots so a starter montage does not drag.
    ranges=[]; total=0.0
    for s in scenes:
        if total>=args.target: break
        start=float(s["start"]); dur=min(float(s["duration"]),3.5,args.target-total)
        if dur<.25: continue
        ranges.append({"source":"main","start":round(start,3),"end":round(start+dur,3),"beat":"VISUAL"})
        total+=dur
    edl={"version":2,"sources":{"main":d["source"]},"ranges":ranges,"grade":"auto",
         "output":{"aspect":args.aspect,"crop_mode":"center"},
         "short_form":{"target_seconds":args.target,"beat_sync":True,"safe_zones":True},"overlays":[]}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(edl,ensure_ascii=False,indent=2))
    print(f"wrote {args.output} | {len(ranges)} ranges | {total:.2f}s")
if __name__=="__main__": main()
