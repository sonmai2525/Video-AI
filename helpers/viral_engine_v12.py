"""V12 Viral Engine: retention-first candidate planning without expensive multi-rendering."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path

def clamp(x,a=0,b=1): return max(a,min(b,float(x)))
def dur(r): return max(.01,(float(r['end'])-float(r['start']))/max(.01,float(r.get('speed',1))))

def build_candidates(edl, analysis, target=20.0):
    ranges=list(edl.get('ranges') or [])
    scenes=analysis.get('scenes') or []
    def scene_for(r):
        st=float(r.get('start',0)); return min(scenes,key=lambda s:abs(float(s.get('start',0))-st)) if scenes else {}
    enriched=[]
    for i,r in enumerate(ranges):
        s=scene_for(r); motion=float(s.get('motion_score',s.get('score',.45)) or .45); change=float(s.get('visual_change',motion) or motion)
        base=float(r.get('story_score_v10',r.get('score',.5)) or .5)
        hook=clamp(.42*base+.34*motion+.24*change)
        enriched.append((dict(r),hook,base,motion))
    if not enriched: return {'version':12,'candidates':[],'winner':None}
    strongest=max(range(len(enriched)),key=lambda i:enriched[i][1])
    # A emotion/story: preserve narrative order, strongest payoff late.
    A=[x[0] for x in enriched]
    # B retention: cold-open strongest, then chronological body; avoid duplicate.
    B=[enriched[strongest][0]]+[x[0] for i,x in enumerate(enriched) if i!=strongest]
    # C compact: prioritize high-value moments but restore chronology after hook.
    keep=sorted(range(len(enriched)),key=lambda i:(enriched[i][1]+enriched[i][2]),reverse=True)
    selected=set(keep[:max(2,math.ceil(len(keep)*.72))]); selected.add(strongest)
    C=[enriched[strongest][0]]+[enriched[i][0] for i in range(len(enriched)) if i in selected and i!=strongest]
    def trim(rs):
        out=[]; used=0
        for r in rs:
            r=dict(r); d=dur(r)
            if used>=target: break
            if used+d>target and target-used>=.35: r['end']=round(float(r['start'])+(target-used)*float(r.get('speed',1)),3); d=target-used
            if used+d<=target+.02: out.append(r); used+=d
        return out
    def score(name,rs):
        if not rs:return 0,{}
        idx=[]
        for r in rs:
            st=float(r.get('start',0)); i=min(range(len(enriched)),key=lambda j:abs(float(enriched[j][0].get('start',0))-st)); idx.append(i)
        first=enriched[idx[0]][1]; avg=sum(enriched[i][1] for i in idx)/len(idx)
        variety=len({round(float(r.get('start',0)),1) for r in rs})/max(1,len(rs))
        pacing=clamp(1-abs((sum(dur(r) for r in rs)/len(rs))-2.2)/3.5)
        continuity=.92 if name=='emotion' else (.80 if name=='retention' else .72)
        total=100*(.34*first+.27*avg+.16*variety+.15*pacing+.08*continuity)
        return round(total,1),{'hook':round(first*100,1),'moment_quality':round(avg*100,1),'variety':round(variety*100,1),'pacing':round(pacing*100,1),'continuity':round(continuity*100,1)}
    candidates=[]
    for name,rs in [('emotion',trim(A)),('retention',trim(B)),('compact',trim(C))]:
        sc,parts=score(name,rs); candidates.append({'name':name,'score':sc,'metrics':parts,'ranges':rs})
    winner=max(candidates,key=lambda x:x['score'])
    return {'version':12,'engine':'viral_engine_v12','strategy':'analyze once, score 3 edit candidates, render winner only','strongest_range_index':strongest,'candidates':candidates,'winner':winner['name'],'winner_score':winner['score']}

def apply(edl,plan):
    out=dict(edl); win=next((x for x in plan.get('candidates',[]) if x['name']==plan.get('winner')),None)
    if not win:return out
    out['ranges']=[dict(r) for r in win['ranges']]
    # Pattern interrupts: sparse, intentional; hook stronger, then one every ~5s max.
    t=0.0
    for i,r in enumerate(out['ranges']):
        if i==0:
            r['beat']='HOOK'; r['motion']='zoom_in'; r['v12_pattern_interrupt']='hook'
        elif t>=5 and i%2==0:
            r.setdefault('motion','push_in'); r['v12_pattern_interrupt']='subtle'; t=0
        t+=dur(r)
    out['viral_v12']={'winner':plan['winner'],'score':plan['winner_score'],'candidate_scores':{x['name']:x['score'] for x in plan['candidates']},'principles':['strongest-moment cold open','retention pacing','sparse pattern interrupts','render winner only']}
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('analysis',type=Path); p.add_argument('edl',type=Path); p.add_argument('-o','--output',type=Path,required=True); p.add_argument('--target',type=float,default=20); p.add_argument('--apply',action='store_true')
    a=p.parse_args(); ed=json.loads(a.edl.read_text()); an=json.loads(a.analysis.read_text()); plan=build_candidates(ed,an,a.target); a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    if a.apply:a.edl.write_text(json.dumps(apply(ed,plan),ensure_ascii=False,indent=2))
    print(f'V12 candidates: '+', '.join(f"{x['name']}={x['score']}" for x in plan['candidates'])+f" | winner={plan['winner']}")
if __name__=='__main__':main()
