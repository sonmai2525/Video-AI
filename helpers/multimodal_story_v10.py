"""V10 Multimodal Story Director.

Builds a reviewable vision packet (contact sheets + JSON), optionally merges scene
understanding supplied by any VLM, then creates a story-first edit: strongest hook
first, chronological body, payoff last, with subject-aware reframing inherited from V9.
No vendor/API is hard-coded; pass --vlm-json to enrich local evidence.
"""
from __future__ import annotations
import argparse,json,math,re
from pathlib import Path
import cv2, numpy as np


def _frame(cap,t):
    cap.set(cv2.CAP_PROP_POS_MSEC,max(0,float(t))*1000); ok,f=cap.read(); return f if ok else None

def _sheet(video, scenes, out_dir:Path):
    out_dir.mkdir(parents=True,exist_ok=True); cap=cv2.VideoCapture(str(video)); refs=[]
    for i,s in enumerate(scenes):
        a,b=float(s['start']),float(s['end']); d=max(.05,b-a); frames=[]
        for k,x in enumerate((.12,.5,.88)):
            f=_frame(cap,a+d*x)
            if f is None: continue
            h,w=f.shape[:2]; nw=360; nh=max(120,round(nw*h/w)); f=cv2.resize(f,(nw,nh))
            cv2.putText(f,f"S{i}  {a+d*x:.2f}s",(10,28),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2,cv2.LINE_AA); frames.append(f)
        if frames:
            mh=max(x.shape[0] for x in frames); frames=[cv2.copyMakeBorder(x,0,mh-x.shape[0],0,0,cv2.BORDER_CONSTANT,value=(20,20,20)) for x in frames]
            p=out_dir/f'scene_{i:03d}.jpg'; cv2.imwrite(str(p),np.hstack(frames)); refs.append({'scene_id':i,'contact_sheet':str(p),'start':a,'end':b})
    cap.release(); return refs

def _vlm_map(vlm):
    return {int(x.get('scene_id',i)):x for i,x in enumerate((vlm or {}).get('scenes') or [])}

def build(video,analysis,story9,semantic8=None,vlm=None,assets_dir=None):
    scenes=analysis.get('scenes') or []; s9={int(x['scene_id']):x for x in (story9 or {}).get('scenes',[])}; sm={int(x.get('scene_id',i)):x for i,x in enumerate((semantic8 or {}).get('scenes') or [])}; vm=_vlm_map(vlm)
    refs=_sheet(video,scenes,assets_dir or Path('v10_storyboards')) if assets_dir is not False else []
    out=[]
    for i,s in enumerate(scenes):
        base=s9.get(int(s.get('id',i)),{}); sem=sm.get(int(s.get('id',i)),{}); rich=vm.get(int(s.get('id',i)),{})
        local=float(base.get('moment_score',.35)); importance=float(rich.get('importance',rich.get('story_score',.5))) if rich else .5
        surprise=float(rich.get('surprise',.5)) if rich else .5; clarity=float(rich.get('clarity',.5)) if rich else .5
        score=float(np.clip(.62*local+.20*importance+.10*surprise+.08*clarity,0,1))
        desc=str(rich.get('description') or rich.get('summary') or '').strip(); action=str(rich.get('action') or '').strip(); headline=str(rich.get('headline') or '').strip()
        if not headline and desc: headline=re.sub(r'\s+',' ',desc)[:52].rstrip(' ,.;:')
        out.append({'scene_id':int(s.get('id',i)),'start':float(s['start']),'end':float(s['end']),'story_score':round(score,3),'local_moment_score':local,
                    'description':desc,'action':action,'headline':headline,'semantic_tags':sem.get('semantic_tags',[]),'focus_x':base.get('focus_x',.5),'focus_y':base.get('focus_y',.5),'tracking_mode':base.get('tracking_mode','locked')})
    # Story grammar: strongest early/overall moment becomes cold-open hook. Body stays chronological; strongest late moment closes.
    if out:
        hook=max(out,key=lambda x:x['story_score']); late=out[max(0,len(out)*2//3):] or out; payoff=max(late,key=lambda x:x['story_score'])
        for x in out: x['narrative_role']='support'
        hook['narrative_role']='hook'; payoff['narrative_role']='payoff' if payoff is not hook else 'hook_payoff'
    else: hook=payoff=None
    return {'version':10,'director':'multimodal_story_v10','source':str(video),'scenes':out,'hook_scene_id':hook['scene_id'] if hook else None,'payoff_scene_id':payoff['scene_id'] if payoff else None,
            'vision_packet':refs,'vlm_enriched':bool(vlm),'capabilities':['contact-sheet vision packet','optional VLM scene semantics','story-score fusion','cold-open hook selection','payoff selection','narrative reorder','headline intent','V9 smart-reframe preservation'],
            'vlm_contract':{'scenes':[{'scene_id':0,'description':'what visibly happens','action':'short action label','importance':0.0,'surprise':0.0,'clarity':0.0,'headline':'optional short on-screen hook'}]}}

def apply(edl,plan,target=20.0):
    out=dict(edl); old=list(out.get('ranges') or []); scenes=plan.get('scenes') or []; by={x['scene_id']:x for x in scenes}
    # Match current ranges to V10 scenes by source start.
    items=[]
    for r in old:
        st=float(r.get('start',0)); m=min(scenes,key=lambda x:abs(x['start']-st)) if scenes else None
        if m: items.append((r,m))
    hid=plan.get('hook_scene_id'); pid=plan.get('payoff_scene_id'); hook=[x for x in items if x[1]['scene_id']==hid]; payoff=[x for x in items if x[1]['scene_id']==pid and x[1]['scene_id']!=hid]
    body=[x for x in items if x[1]['scene_id'] not in {hid,pid}]; body.sort(key=lambda z:z[1]['start'])
    ordered=hook+body+payoff
    ranges=[]; used=0.0
    for r,m in ordered:
        nr=dict(r); dur=(float(nr['end'])-float(nr['start']))/max(.01,float(nr.get('speed',1)))
        if used>=target: break
        if used+dur>target and target-used>=.30: nr['end']=round(float(nr['start'])+(target-used)*float(nr.get('speed',1)),3); dur=target-used
        nr.update({'scene_id':m['scene_id'],'story_score_v10':m['story_score'],'narrative_role_v10':m['narrative_role'],'focus_x':m['focus_x'],'focus_y':m['focus_y'],'tracking_mode':m['tracking_mode']})
        if m['narrative_role'].startswith('hook'): nr['motion']='zoom_in'; nr['beat']='HOOK'
        elif m['narrative_role']=='payoff': nr['beat']='PAYOFF'
        ranges.append(nr); used+=dur
    out['ranges']=ranges
    # Headline intent for transcript-backed dynamic captions; no fabricated text when VLM did not provide semantics.
    events=list(out.get('caption_events') or []); offset=0.0
    for r in ranges:
        dur=(float(r['end'])-float(r['start']))/max(.01,float(r.get('speed',1))); m=by.get(r['scene_id'])
        if m and m.get('headline') and (m['narrative_role'].startswith('hook') or m['narrative_role']=='payoff'):
            events.append({'start':round(offset,3),'end':round(min(offset+1.4,offset+dur),3),'role':'hook' if m['narrative_role'].startswith('hook') else 'emphasis','generated_headline':m['headline']})
        offset+=dur
    out['caption_events']=events; out['multimodal_story_v10']={'version':10,'director':plan['director'],'hook_scene_id':hid,'payoff_scene_id':pid,'vlm_enriched':plan.get('vlm_enriched',False),'scenes':scenes}
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('video',type=Path); p.add_argument('analysis',type=Path); p.add_argument('story9',type=Path); p.add_argument('-o','--output',type=Path,required=True); p.add_argument('--semantic',type=Path); p.add_argument('--vlm-json',type=Path); p.add_argument('--assets-dir',type=Path); p.add_argument('--edl',type=Path); p.add_argument('--apply',action='store_true'); p.add_argument('--target',type=float,default=20)
    a=p.parse_args(); load=lambda x:json.loads(x.read_text()) if x and x.exists() else None
    plan=build(a.video,load(a.analysis),load(a.story9),load(a.semantic),load(a.vlm_json),a.assets_dir or a.output.parent/'v10_storyboards'); a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)); print(f'wrote {a.output} | {len(plan["scenes"])} V10 scenes | VLM={plan["vlm_enriched"]}')
    if a.edl and a.apply: a.edl.write_text(json.dumps(apply(load(a.edl),plan,a.target),ensure_ascii=False,indent=2)); print(f'applied V10 narrative edit → {a.edl}')
if __name__=='__main__': main()
