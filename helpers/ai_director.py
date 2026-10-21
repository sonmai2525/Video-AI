"""V5 AI Director: turn scene analysis into a scene-aware visual direction plan.

This local director is deterministic and dependency-light. It samples each scene,
finds faces (when OpenCV Haar data is available), estimates visual clutter/negative
space, and chooses safe text placement + restrained motion. A cloud/multimodal
model can later replace/augment these decisions while keeping the same JSON contract.

Usage:
  python helpers/ai_director.py input.mp4 edit/analysis.json -o edit/director.json
  python helpers/ai_director.py input.mp4 edit/analysis.json --edl edit/edl.json --apply
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import cv2
import numpy as np

CANDIDATES={
 "upper":(.50,.29), "left":(.28,.47), "right":(.72,.47),
 "lower_safe":(.50,.69), "top_left":(.28,.27), "top_right":(.72,.27), "center":(.50,.48)
}

def _frame_at(cap, t: float):
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0,t)*1000.0)
    ok, frame=cap.read(); return frame if ok else None

def _faces(gray):
    try:
        cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
        if cascade.empty(): return []
        return [tuple(map(int,x)) for x in cascade.detectMultiScale(gray,1.12,4,minSize=(28,28))]
    except Exception: return []

def _roi_score(edge, faces, cx, cy, rw=.46, rh=.18):
    h,w=edge.shape; x0=int((cx-rw/2)*w); x1=int((cx+rw/2)*w); y0=int((cy-rh/2)*h); y1=int((cy+rh/2)*h)
    x0=max(0,x0); y0=max(0,y0); x1=min(w,x1); y1=min(h,y1)
    roi=edge[y0:y1,x0:x1]; clutter=float(np.mean(roi)/255.0) if roi.size else 1.0
    overlap=0.0
    area=max(1,(x1-x0)*(y1-y0))
    for fx,fy,fw,fh in faces:
        ix=max(0,min(x1,fx+fw)-max(x0,fx)); iy=max(0,min(y1,fy+fh)-max(y0,fy))
        overlap += ix*iy/area
    # Faces are a much stronger penalty than texture.
    return clutter + overlap*5.0

def inspect_frame(frame):
    h,w=frame.shape[:2]; small=cv2.resize(frame,(360,max(180,round(360*h/w))))
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    edge=cv2.Canny(gray,70,150)
    faces=_faces(gray)
    scores={name:round(_roi_score(edge,faces,*xy),4) for name,xy in CANDIDATES.items()}
    # center is intentionally slightly discouraged so text doesn't constantly cover subjects.
    scores['center']=round(scores['center']+.08,4)
    best=min(scores,key=scores.get)
    face_norm=[]
    sh,sw=gray.shape
    for x,y,fw,fh in faces: face_norm.append({'x':round(x/sw,3),'y':round(y/sh,3),'w':round(fw/sw,3),'h':round(fh/sh,3)})
    return {'layout':best,'scores':scores,'faces':face_norm,'edge_density':round(float(np.mean(edge)/255.0),4)}

def near_beat(t, beats, tol=.12):
    return any(abs(float(b)-t)<=tol for b in beats)

def direct(video: Path, analysis: dict):
    cap=cv2.VideoCapture(str(video)); beats=analysis.get('audio',{}).get('beats') or []
    scenes=analysis.get('scenes') or [] ; events=[]; inspections=[]
    for i,s in enumerate(scenes):
        a=float(s['start']); b=float(s['end']); mid=(a+b)/2
        frame=_frame_at(cap,mid)
        vis=inspect_frame(frame) if frame is not None else {'layout':'upper','scores':{},'faces':[],'edge_density':None}
        dur=b-a
        if i==0: style,motion='hook','rise'
        elif i==len(scenes)-1: style,motion='cta','pop'
        elif near_beat(a,beats): style,motion='viral_pop','pop'
        elif dur>=2.5: style,motion='clean','drift'
        else: style,motion='viral_pop',('slide_left' if i%2 else 'slide_right')
        ev={'start':round(a,3),'end':round(b,3),'layout':vis['layout'],'motion':motion,'style':style,
            'reason':'negative_space','confidence':round(max(.35,1.0-min(vis.get('scores',{}).get(vis['layout'],.6),.65)),2)}
        events.append(ev); inspections.append({'scene_id':s.get('id',i),'time':round(mid,3),**vis})
    cap.release()
    return {'version':5,'director':'local_visual_director','source':str(video),'visual_text_events':events,
            'scene_inspections':inspections,'policy':{'avoid_faces':True,'prefer_negative_space':True,'safe_area':True,
            'motion_density':'restrained','first_scene':'hook','last_scene':'cta'},
            'notes':['V5 local director uses visual geometry, not semantic image understanding.',
                     'A multimodal model may override style/layout while preserving visual_text_events schema.',
                     'Review low-confidence placements before final render.']}

def apply_to_edl(edl: dict, plan: dict):
    edl=dict(edl); edl['caption_style']='visual_dynamic'; edl['visual_text_events']=plan['visual_text_events']
    edl['director']={'version':5,'name':plan['director'],'policy':plan['policy']}
    return edl

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('video',type=Path); ap.add_argument('analysis',type=Path)
    ap.add_argument('-o','--output',type=Path); ap.add_argument('--edl',type=Path); ap.add_argument('--apply',action='store_true')
    args=ap.parse_args(); analysis=json.loads(args.analysis.read_text()); plan=direct(args.video,analysis)
    out=args.output or args.analysis.with_name('director.v5.json'); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(plan,ensure_ascii=False,indent=2)); print(f'wrote {out} | {len(plan["visual_text_events"])} directed scenes')
    if args.edl and args.apply:
        edl=json.loads(args.edl.read_text()); merged=apply_to_edl(edl,plan); args.edl.write_text(json.dumps(merged,ensure_ascii=False,indent=2)); print(f'applied V5 director → {args.edl}')
if __name__=='__main__': main()
