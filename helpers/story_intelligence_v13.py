"""V13 Story Intelligence: chronology lock, payoff protection, sparse effects, edit critic."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import cv2, numpy as np

def clamp(x,a=0,b=1): return max(a,min(b,float(x)))
def rdur(r): return max(.01,(float(r['end'])-float(r['start']))/max(.01,float(r.get('speed',1))))
def _detail(video,t):
 cap=cv2.VideoCapture(str(video)); cap.set(cv2.CAP_PROP_POS_MSEC,max(0,t)*1000); ok,f=cap.read(); cap.release()
 if not ok:return None
 g=cv2.cvtColor(cv2.resize(f,(256,256)),cv2.COLOR_BGR2GRAY); return float(cv2.Laplacian(g,cv2.CV_32F).var())
def classify(video,analysis):
 vals=[]
 for s in analysis.get('scenes') or []:
  d=_detail(video,(float(s['start'])+float(s['end']))/2)
  if d is not None: vals.append(d)
 if len(vals)<5:return {'type':'general','confidence':.35,'detail_trend':0,'detail_gain':0}
 y=np.asarray(vals); x=np.arange(len(y)); corr=float(np.corrcoef(x,y)[0,1]) if np.std(y)>1e-9 else 0; q=max(1,len(y)//4); gain=(float(np.median(y[-q:]))-float(np.median(y[:q])))/max(1,float(np.median(y[:q])))
 process=(corr>.20 and gain>.10) or corr>.38; conf=clamp(.48+.42*max(0,corr)+.22*max(0,gain)) if process else clamp(.45+.25*abs(corr))
 return {'type':'process' if process else 'general','confidence':round(conf,3),'detail_trend':round(corr,3),'detail_gain':round(gain,3),'samples':len(vals)}
def _chronology(rs):
 if len(rs)<2:return 1.0
 a=[float(r['start']) for r in rs]; return sum(y>=x-.08 for x,y in zip(a,a[1:]))/(len(a)-1)
def protect_process(edl,target,teaser=.55):
 rs=sorted([dict(r) for r in edl.get('ranges') or []],key=lambda r:float(r['start']))
 if not rs:return rs
 payoff=rs[-1]; body=rs[:-1]; out=[]
 if target>=8 and rdur(payoff)>.35:
  p=dict(payoff); p['start']=max(float(p['start']),float(p['end'])-teaser*float(p.get('speed',1))); p.update(beat='TEASER',motion='none',v13_payoff_teaser=True); out.append(p)
 reveal=min(2.0,max(.9,target*.09)); budget=max(1,target-sum(rdur(x) for x in out)-reveal); used=0
 for r in body:
  d=rdur(r)
  if used>=budget:break
  x=dict(r)
  if used+d>budget:
   rem=budget-used
   if rem<.28:break
   x['end']=float(x['start'])+rem*float(x.get('speed',1)); d=rem
  out.append(x); used+=d
 p=dict(payoff)
 if rdur(p)>reveal:p['start']=float(p['end'])-reveal*float(p.get('speed',1))
 p.update(beat='PAYOFF',motion='none',v13_payoff_protected=True); out.append(p); return out
def critique(edl,story):
 rs=edl.get('ranges') or []; core=[r for r in rs if not r.get('v13_payoff_teaser')]; ch=_chronology(core); issues=[]; score=100
 if story.get('type')=='process' and ch<.92:issues.append({'code':'BROKEN_PROCESS_ORDER','severity':'error'}); score-=28
 if story.get('type')=='process' and rs and rdur(rs[0])>.8 and rs[0].get('beat')=='TEASER':issues.append({'code':'PAYOFF_SPOILED','severity':'error'}); score-=24
 long=[r for r in rs if rdur(r)>3.2]
 if long:issues.append({'code':'SLOW_MOMENTS','severity':'warn','count':len(long)}); score-=min(12,4*len(long))
 fx=sum(1 for r in rs if r.get('motion') not in (None,'none'))
 if rs and fx/len(rs)>.65:issues.append({'code':'TOO_MANY_MOTION_EFFECTS','severity':'warn'}); score-=8
 return {'score':max(0,score),'chronology':round(ch*100,1),'issues':issues,'pass':score>=82 and not any(x['severity']=='error' for x in issues)}
def apply(edl,video,analysis,target=20):
 story=classify(video,analysis); out=dict(edl)
 if story['type']=='process':out['ranges']=protect_process(out,target)
 t=0
 for i,r in enumerate(out.get('ranges') or []):
  if r.get('beat') in ('TEASER','PAYOFF'):r['motion']='none'
  elif i and t>=5.5:r.setdefault('motion','zoom_in'); r['v13_pattern_interrupt']='content_driven'; t=0
  t+=rdur(r)
 out['v13_caption_policy']={'mode':'minimal_story' if story['type']=='process' else 'adaptive','rule':'prefer silence over generic poetry','max_non_speech_cards':3}; out['story_v13']=story; out['critic_v13']=critique(out,story); return out
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('video',type=Path); ap.add_argument('analysis',type=Path); ap.add_argument('edl',type=Path); ap.add_argument('-o','--output',type=Path,required=True); ap.add_argument('--target',type=float,default=20); ap.add_argument('--apply',action='store_true'); a=ap.parse_args(); an=json.loads(a.analysis.read_text()); ed=json.loads(a.edl.read_text()); out=apply(ed,a.video,an,a.target); a.output.write_text(json.dumps({'version':13,'story':out['story_v13'],'critic':out['critic_v13'],'caption_policy':out['v13_caption_policy']},ensure_ascii=False,indent=2));
 if a.apply:a.edl.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(f"V13 story={out['story_v13']['type']} conf={out['story_v13']['confidence']} critic={out['critic_v13']['score']}/100")
if __name__=='__main__':main()
