"""V9 Story + Smart Reframe Director.

Local, reviewable multimodal-style fusion: samples each scene across time and combines
visual saliency, face presence/position, motion, audio beats and scene duration into
moment/story scores. It also produces subject-aware crop focus coordinates so 9:16
reframing follows the likely subject instead of always center-cropping.

This is intentionally provider-neutral: a future vision-language model can add
`semantic_summary`/`story_role` while preserving this JSON contract.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import cv2, numpy as np
from ai_director import _faces


def _frame(cap,t):
    cap.set(cv2.CAP_PROP_POS_MSEC,max(0,float(t))*1000); ok,f=cap.read(); return f if ok else None

def _subject(frame):
    """Return normalized likely-subject center + confidence, preferring faces."""
    h,w=frame.shape[:2]; small=cv2.resize(frame,(480,max(180,round(480*h/w))))
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY); sh,sw=gray.shape
    faces=_faces(gray)
    if faces:
        # largest face is the safest human-subject cue
        x,y,fw,fh=max(faces,key=lambda z:z[2]*z[3])
        return (x+fw/2)/sw,(y+fh/2)/sh,min(.98,.72+fw*fh/(sw*sh)*2.0),'face'
    # Spectral-residual saliency if available, otherwise gradient-energy centroid.
    try:
        sal=cv2.saliency.StaticSaliencySpectralResidual_create(); ok,m=sal.computeSaliency(small)
        heat=m.astype(np.float32) if ok else None
    except Exception: heat=None
    if heat is None:
        gx=cv2.Sobel(gray,cv2.CV_32F,1,0); gy=cv2.Sobel(gray,cv2.CV_32F,0,1); heat=cv2.magnitude(gx,gy)
    heat=cv2.GaussianBlur(heat,(0,0),9); total=float(heat.sum())
    if total<=1e-6:return .5,.5,.25,'center_fallback'
    yy,xx=np.indices(heat.shape); cx=float((heat*xx).sum()/total/sw); cy=float((heat*yy).sum()/total/sh)
    # Avoid unstable edge locking.
    cx=float(np.clip(cx,.12,.88)); cy=float(np.clip(cy,.12,.88))
    return cx,cy,.48,'saliency'

def _motion(a,b):
    if a is None or b is None:return 0.0
    ga=cv2.cvtColor(cv2.resize(a,(320,180)),cv2.COLOR_BGR2GRAY); gb=cv2.cvtColor(cv2.resize(b,(320,180)),cv2.COLOR_BGR2GRAY)
    return float(np.mean(cv2.absdiff(ga,gb))/255.0)

def build(video,analysis,semantic=None):
    cap=cv2.VideoCapture(str(video)); beats=[float(x) for x in analysis.get('audio',{}).get('beats') or []]
    sem_by={int(x.get('scene_id',i)):x for i,x in enumerate((semantic or {}).get('scenes') or [])}; out=[]
    scenes=analysis.get('scenes') or []
    for i,s in enumerate(scenes):
        sid=int(s.get('id',i)); a,b=float(s['start']),float(s['end']); d=max(.05,b-a)
        ts=[a+d*x for x in (.08,.28,.5,.72,.92)]; frames=[_frame(cap,t) for t in ts]
        obs=[_subject(f) for f in frames if f is not None]
        xs=[o[0] for o in obs] or [.5]; ys=[o[1] for o in obs] or [.5]; confs=[o[2] for o in obs] or [.25]
        # Median is robust to one bad saliency frame; clamp to crop-safe bounds.
        fx=float(np.clip(np.median(xs),.18,.82)); fy=float(np.clip(np.median(ys),.20,.80))
        travel=float(max(xs)-min(xs)) if xs else 0; mot=np.mean([_motion(x,y) for x,y in zip(frames,frames[1:])]) if len(frames)>1 else 0
        beat=min([abs(a-z) for z in beats],default=9)<.13
        sem=sem_by.get(sid,{}); faces=float(sem.get('face_count',0)>0)
        duration_fit=max(0,1-abs(min(d,3)-1.35)/2.2)
        score=float(np.clip(.28*duration_fit+.28*min(1,mot/.11)+.18*faces+.14*beat+.12*np.mean(confs),0,1))
        role='hook_candidate' if i<max(1,min(3,len(scenes))) and score>=.48 else ('payoff_candidate' if i>=len(scenes)-2 and score>=.45 else ('highlight' if score>=.58 else 'support'))
        out.append({'scene_id':sid,'start':round(a,3),'end':round(b,3),'moment_score':round(score,3),'story_role':role,
                    'focus_x':round(fx,4),'focus_y':round(fy,4),'subject_travel':round(travel,4),'tracking_mode':('follow' if travel>.12 else 'locked'),
                    'subject_confidence':round(float(np.mean(confs)),3),'subject_cue':max(set([o[3] for o in obs]),key=[o[3] for o in obs].count) if obs else 'none',
                    'motion_score':round(float(mot),4),'beat_entry':beat})
    cap.release()
    return {'version':9,'director':'story_reframe_v9','source':str(video),'scenes':out,
            'capabilities':['multi-frame subject localization','face-priority saliency','moment scoring','audio/visual fusion','story-role hints','subject-aware smart reframe'],
            'limitations':['Local V9 infers likely subjects and moment strength but does not claim human-level narrative understanding.','Arbitrary object naming/action descriptions require an optional vision-language provider.']}

def apply(edl,plan):
    out=dict(edl); scenes=plan['scenes']; byid={int(x['scene_id']):x for x in scenes}
    ranges=out.get('ranges') or []
    for r in ranges:
        sid=r.get('scene_id'); m=byid.get(int(sid)) if sid is not None else None
        if m is None:
            st=float(r.get('start',0)); m=min(scenes,key=lambda x:abs(x['start']-st)) if scenes else None
        if not m: continue
        r['focus_x']=m['focus_x']; r['focus_y']=m['focus_y']; r['tracking_mode']=m['tracking_mode']; r['moment_score']=m['moment_score']; r['story_role_v9']=m['story_role']
        # Keep effects restrained on weak moments; add subtle motion to strong static moments.
        if m['moment_score']<.36:r['motion']='none'
        elif m['moment_score']>.68 and r.get('motion','none')=='none':r['motion']='zoom_in'
    out['ranges']=ranges; out['story_reframe_v9']={'version':9,'director':plan['director'],'scenes':scenes}
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('video',type=Path);ap.add_argument('analysis',type=Path);ap.add_argument('-o','--output',type=Path,required=True);ap.add_argument('--semantic',type=Path);ap.add_argument('--edl',type=Path);ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    analysis=json.loads(a.analysis.read_text()); sem=json.loads(a.semantic.read_text()) if a.semantic and a.semantic.exists() else None
    plan=build(a.video,analysis,sem);a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2));print(f'wrote {a.output} | {len(plan["scenes"])} V9 story/reframe scenes')
    if a.edl and a.apply:
        a.edl.write_text(json.dumps(apply(json.loads(a.edl.read_text()),plan),ensure_ascii=False,indent=2));print(f'applied V9 smart reframe → {a.edl}')
if __name__=='__main__':main()
