"""V13.1 Finish Director: micro-hook, visual-progress pacing, smart text zones, cinematic reveal."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import cv2, numpy as np


def clamp(x,a=0,b=1): return max(a,min(b,float(x)))
def rdur(r): return max(.01,(float(r['end'])-float(r['start']))/max(.01,float(r.get('speed',1))))

def frame(video,t,w=270,h=480):
    cap=cv2.VideoCapture(str(video)); cap.set(cv2.CAP_PROP_POS_MSEC,max(0,float(t))*1000); ok,f=cap.read(); cap.release()
    if not ok:return None
    return cv2.resize(f,(w,h),interpolation=cv2.INTER_AREA)

def progress(video,r):
    a=float(r['start']); b=float(r['end']); d=max(.05,b-a); f1=frame(video,a+.12*d); f2=frame(video,b-.12*d)
    if f1 is None or f2 is None:return .5
    g1=cv2.cvtColor(f1,cv2.COLOR_BGR2GRAY); g2=cv2.cvtColor(f2,cv2.COLOR_BGR2GRAY)
    diff=float(np.mean(cv2.absdiff(g1,g2)))/255.0
    e1=cv2.Canny(g1,70,150); e2=cv2.Canny(g2,70,150); edge=float(np.mean(cv2.absdiff(e1,e2)))/255.0
    return clamp(diff*2.6+edge*.9)

def quiet_zone(video,t):
    f=frame(video,t)
    if f is None:return 'upper'
    g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY); e=cv2.Canny(g,60,140); h,w=e.shape
    zones={'upper':e[int(.12*h):int(.38*h),:], 'center':e[int(.38*h):int(.65*h),:], 'lower_safe':e[int(.65*h):int(.86*h),:]}
    return min(zones,key=lambda k:float(np.mean(zones[k])))

def tune_process(edl,video,target=20.0):
    rs=[dict(r) for r in edl.get('ranges') or []]
    if not rs:return rs,[]
    # Keep teaser tiny: enough to promise quality, not enough to consume the payoff.
    if rs[0].get('v13_payoff_teaser') or rs[0].get('beat')=='TEASER':
        x=rs[0]; keep=.40; x['start']=max(float(x['start']),float(x['end'])-keep*float(x.get('speed',1))); x['motion']='none'; x['v131_micro_hook']=True
    vals=[]
    for i,r in enumerate(rs):
        if r.get('beat') in ('TEASER','PAYOFF'): vals.append((i,1.0)); continue
        p=progress(video,r); vals.append((i,p)); r['v131_visual_progress']=round(p,3)
        # Compress visually stagnant process steps, preserve meaningful transformations.
        d=rdur(r)
        if p<.18 and d>1.0:
            want=max(.62,d*(.58+.9*p)); r['end']=float(r['start'])+want*float(r.get('speed',1)); r['v131_progress_compressed']=True
        elif p>.48 and d<1.05:
            r['v131_hold_priority']='high_progress'
    # Reveal: clean, calm, long enough to enjoy; no template motion.
    payoff=next((r for r in reversed(rs) if r.get('beat')=='PAYOFF'),rs[-1]); reveal=min(2.0,max(1.55,target*.085))
    if rdur(payoff)>reveal: payoff['start']=float(payoff['end'])-reveal*float(payoff.get('speed',1))
    payoff['motion']='none'; payoff['v131_cinematic_reveal']=True
    # Content-driven pattern interrupts only on high-progress body moments.
    elapsed=0.0
    for r in rs:
        if r.get('beat') in ('TEASER','PAYOFF'): elapsed+=rdur(r); continue
        p=float(r.get('v131_visual_progress',.5))
        if elapsed>=4.8 and p>=.32:
            r['motion']='zoom_in' if p>.5 else 'push_in'; r['v131_pattern_interrupt']='progress_driven'; elapsed=0
        elif p<.2: r['motion']='none'
        elapsed+=rdur(r)
    return rs,vals

def text_plan(edl,video):
    # Position existing/generated captions in low-detail zones. Keep process videos sparse.
    events=[]; offset=0.0; ranges=edl.get('ranges') or []
    for i,r in enumerate(ranges):
        d=rdur(r); mid=(float(r['start'])+float(r['end']))/2
        if r.get('beat')=='TEASER':
            events.append({'start':offset,'end':min(offset+d,offset+1.05),'layout':quiet_zone(video,mid),'motion':'rise','style':'hook','confidence':.95,'v131':'micro_hook'})
        elif r.get('beat')=='PAYOFF':
            # Reveal should breathe; if text exists, keep it understated and away from subject.
            events.append({'start':offset,'end':offset+d,'layout':quiet_zone(video,mid),'motion':'drift','style':'cinematic','confidence':.9,'v131':'reveal'})
        elif len(events)<2 and float(r.get('v131_visual_progress',0))>.42 and offset>4:
            events.append({'start':offset,'end':min(offset+d,offset+1.35),'layout':quiet_zone(video,mid),'motion':'rise','style':'clean','confidence':.82,'v131':'progress'})
        offset+=d
    return events[:3]

def apply(edl,video,target=20.0):
    out=dict(edl); story=(out.get('story_v13') or {})
    if story.get('type')=='process':
        out['ranges'],vals=tune_process(out,video,target)
        out['visual_text_events']=text_plan(out,video)
        out['v131_caption_policy']={'max_cards':3,'hook_max_seconds':1.05,'prefer_silence':True,'avoid_generic_poetry':True,'placement':'lowest-detail-safe-zone'}
        out['v131_reveal_policy']={'duration_seconds':'1.55-2.0','motion':'none','purpose':'payoff must breathe'}
        out['v131_progress_summary']={'samples':len(vals),'low_progress_ranges':sum(v<.18 for _,v in vals),'high_progress_ranges':sum(v>.48 for _,v in vals)}
    out['finish_director_v131']={'version':'13.1','micro_hook':True,'visual_progress_pacing':True,'smart_caption_placement':True,'cinematic_reveal':True}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('video',type=Path); ap.add_argument('edl',type=Path); ap.add_argument('-o','--output',type=Path,required=True); ap.add_argument('--target',type=float,default=20); ap.add_argument('--apply',action='store_true'); a=ap.parse_args()
    ed=json.loads(a.edl.read_text()); out=apply(ed,a.video,a.target); report={'version':'13.1','finish_director':out.get('finish_director_v131'),'caption_policy':out.get('v131_caption_policy'),'reveal_policy':out.get('v131_reveal_policy'),'progress':out.get('v131_progress_summary')}; a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if a.apply:a.edl.write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print('V13.1 finish director applied:',report)
if __name__=='__main__':main()
