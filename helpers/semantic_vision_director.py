"""V8 Semantic Vision Director.

Dependency-light visual understanding for short-form editing. It samples each scene
at multiple times and derives interpretable semantic signals: people/faces, likely
subject region, motion/action intensity, shot scale, brightness, visual complexity,
text-safe negative space, and saliency. It then emits a stable JSON contract that
can later be enriched by a multimodal model without changing downstream tools.

Usage:
 python helpers/semantic_vision_director.py input.mp4 analysis.json -o semantic.v8.json --edl edl.json --apply
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import cv2, numpy as np
from ai_director import inspect_frame

def _frame(cap,t):
    cap.set(cv2.CAP_PROP_POS_MSEC,max(0,t)*1000); ok,f=cap.read(); return f if ok else None

def _gray_small(f,w=320):
    h0,w0=f.shape[:2]; return cv2.cvtColor(cv2.resize(f,(w,max(120,round(w*h0/w0)))),cv2.COLOR_BGR2GRAY)

def _motion(frames):
    gs=[_gray_small(f) for f in frames if f is not None]
    if len(gs)<2:return 0.0
    vals=[float(np.mean(cv2.absdiff(a,b)))/255 for a,b in zip(gs,gs[1:])]
    return float(np.mean(vals))

def _saliency_region(frame):
    g=_gray_small(frame,360); lap=cv2.Laplacian(g,cv2.CV_32F); mag=np.abs(lap)
    h,w=mag.shape; cells=[]
    for iy in range(3):
      for ix in range(3):
        r=mag[iy*h//3:(iy+1)*h//3,ix*w//3:(ix+1)*w//3]
        cells.append((float(np.mean(r)),ix,iy))
    _,ix,iy=max(cells)
    names={(0,0):'top_left',(1,0):'upper',(2,0):'top_right',(0,1):'left',(1,1):'center',(2,1):'right',(0,2):'bottom_left',(1,2):'lower',(2,2):'bottom_right'}
    return names[(ix,iy)]

def inspect_scene(cap,s):
    a,b=float(s['start']),float(s['end']); dur=max(.01,b-a)
    ts=[a+dur*x for x in (.22,.5,.78)]; fs=[_frame(cap,t) for t in ts]; fs=[f for f in fs if f is not None]
    if not fs:return {'semantic_tags':['unknown'],'subject_region':'center','safe_text_layout':'upper','motion_score':0,'action_level':'low','face_count':0,'shot_scale':'unknown','brightness':'unknown','complexity':0,'confidence':.25}
    vis=[inspect_frame(f) for f in fs]; face_count=max(len(v['faces']) for v in vis); edge=float(np.mean([v['edge_density'] for v in vis])); mot=_motion(fs)
    bright=float(np.mean([np.mean(_gray_small(f))/255 for f in fs])); sal=_saliency_region(fs[len(fs)//2]); safe=min(vis[len(vis)//2]['scores'],key=vis[len(vis)//2]['scores'].get)
    tags=[]
    if face_count: tags += ['person','face']
    if mot>.10: tags += ['high_motion','action']
    elif mot>.045: tags += ['motion']
    else: tags += ['static']
    if edge>.13: tags.append('detailed_scene')
    elif edge<.06: tags.append('clean_scene')
    if bright<.25: tags.append('dark_scene')
    elif bright>.75: tags.append('bright_scene')
    # Conservative shot-scale estimate from largest detected face.
    areas=[f['w']*f['h'] for v in vis for f in v['faces']]
    ma=max(areas) if areas else 0
    shot='close_up' if ma>.08 else ('medium' if ma>.018 else ('wide' if face_count else 'environment/object'))
    action='high' if mot>.10 else ('medium' if mot>.045 else 'low')
    conf=min(.95,.52 + .08*len(fs) + (.08 if face_count else 0))
    return {'semantic_tags':tags,'subject_region':sal,'safe_text_layout':safe,'motion_score':round(mot,4),'action_level':action,'face_count':face_count,'shot_scale':shot,'brightness':('dark' if bright<.25 else 'bright' if bright>.75 else 'normal'),'complexity':round(edge,4),'confidence':round(conf,2)}

def direct(video,analysis):
    cap=cv2.VideoCapture(str(video)); out=[]
    for i,s in enumerate(analysis.get('scenes') or []):
        sem=inspect_scene(cap,s); out.append({'scene_id':s.get('id',i),'start':float(s['start']),'end':float(s['end']),**sem})
    cap.release()
    return {'version':8,'director':'semantic_vision_director','source':str(video),'scenes':out,'capabilities':['multi-frame scene inspection','face/person cue','subject-region saliency','motion/action cue','shot-scale cue','negative-space text placement','brightness/complexity cue'],'limitations':['Local V8 uses interpretable computer-vision cues; it does not name arbitrary objects or infer private/sensitive attributes.','A multimodal semantic provider can enrich semantic_tags later using the same JSON contract.']}

def apply(edl,plan):
    edl=dict(edl); by=[x for x in plan['scenes']]
    edl['semantic_vision']={'version':8,'director':plan['director'],'scenes':by}
    # Override V5 placement with V8 multi-frame safe placement; adapt motion conservatively.
    events=list(edl.get('visual_text_events') or [])
    for ev,sem in zip(events,by):
        ev['layout']=sem['safe_text_layout']; ev['semantic_subject_region']=sem['subject_region']; ev['semantic_confidence']=sem['confidence']
        if sem['action_level']=='high': ev['motion']='pop'
        elif sem['shot_scale']=='close_up': ev['motion']='rise'
    edl['visual_text_events']=events
    # Enrich edit clips when they overlap a semantic scene.
    clips=edl.get('clips') or edl.get('segments') or []
    for c in clips:
        st=float(c.get('start',c.get('source_start',0))); match=next((x for x in by if x['start']-.05<=st<=x['end']+.05),None)
        if match:
            c['semantic_tags']=match['semantic_tags']; c['subject_region']=match['subject_region']; c['action_level']=match['action_level']
            if match['action_level']=='high': c.setdefault('camera_motion','zoom_in')
    edl['director_v8']={'name':plan['director'],'version':8}
    return edl

def main():
    p=argparse.ArgumentParser(); p.add_argument('video',type=Path);p.add_argument('analysis',type=Path);p.add_argument('-o','--output',type=Path,required=True);p.add_argument('--edl',type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
    plan=direct(a.video,json.loads(a.analysis.read_text()));a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2));print(f'wrote {a.output} | {len(plan["scenes"])} semantic scenes')
    if a.edl and a.apply:
        a.edl.write_text(json.dumps(apply(json.loads(a.edl.read_text()),plan),ensure_ascii=False,indent=2));print(f'applied V8 semantic vision → {a.edl}')
if __name__=='__main__':main()
