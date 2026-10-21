"""V6 Creative Director for short-form edits.

Builds a creative edit plan from V2 analysis + optional V5 visual inspections.
It ranks shots, chooses pacing, beat-aware trim points, playback speed, subtle
camera motion, transition intent, sound-design cues, color mood and hook/ending
roles. The output is deterministic and reviewable; it does not pretend to have
semantic vision when no multimodal model is connected.

Usage:
  python helpers/creative_director.py edit/analysis.json -o edit/creative.v6.json
  python helpers/creative_director.py edit/analysis.json --director edit/director.v5.json --edl edit/edl.json --apply
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path


def _nearest_beat(t, beats, max_delta=.22):
    if not beats: return t
    b=min((float(x) for x in beats), key=lambda x:abs(x-t))
    return b if abs(b-t)<=max_delta else t


def _inspection_map(director):
    return {int(x.get('scene_id',i)):x for i,x in enumerate((director or {}).get('scene_inspections') or [])}


def _energy(scene, vis, i, n, beats):
    dur=max(.05,float(scene['duration']))
    edge=vis.get('edge_density')
    edge=.18 if edge is None else float(edge)
    # Prefer visually informative medium shots. Very long/static and tiny flash shots lose points.
    duration_score=max(0.0,1.0-abs(min(dur,4.0)-1.35)/3.0)
    beat_bonus=.12 if any(abs(float(b)-float(scene['start']))<.14 for b in beats) else 0
    opening=.16 if i==0 else 0; ending=.08 if i==n-1 else 0
    return round(min(1.0,.42*duration_score+.42*min(1,edge*3.2)+beat_bonus+opening+ending),3)


def build_plan(analysis, director=None, target=20.0):
    scenes=analysis.get('scenes') or []; beats=analysis.get('audio',{}).get('beats') or []
    bpm=analysis.get('audio',{}).get('tempo_bpm'); ins=_inspection_map(director)
    ranked=[]
    for i,s in enumerate(scenes):
        score=_energy(s,ins.get(int(s.get('id',i)),{}),i,len(scenes),beats)
        ranked.append((score,i,s))
    # Preserve chronology after selection; opening/ending scenes remain useful story anchors.
    chosen=[]; used=0.0
    for score,i,s in sorted(ranked,reverse=True):
        if used>=target: break
        max_len=1.7 if (bpm or 0)>=115 else 2.35
        keep=min(float(s['duration']),max_len,max(.35,target-used))
        if keep>=.28: chosen.append((i,score,s,keep)); used+=keep
    chosen.sort(key=lambda x:x[0])
    edits=[]
    for j,(i,score,s,keep) in enumerate(chosen):
        start=float(s['start']); end=min(float(s['end']),start+keep)
        # Snap endings near beats but never leave the scene.
        snapped=_nearest_beat(end,beats)
        if start+.28 < snapped <= float(s['end']): end=snapped
        role='hook' if j==0 else ('payoff' if j==len(chosen)-1 else ('highlight' if score>=.62 else 'support'))
        if role=='hook': speed=1.0; motion='zoom_in'; transition='hard_cut'
        elif score>=.72: speed=.88; motion='zoom_in'; transition='impact_cut'
        elif score<.42: speed=1.18; motion='none'; transition='hard_cut'
        else: speed=1.0; motion=('zoom_out' if j%3==0 else 'none'); transition='beat_cut'
        sfx=None
        if role=='hook': sfx='whoosh_soft'
        elif transition=='impact_cut': sfx='impact_light'
        elif transition=='beat_cut' and j%3==0: sfx='tick'
        edits.append({'scene_id':s.get('id',i),'source':'main','start':round(start,3),'end':round(end,3),
                      'score':score,'role':role,'speed':speed,'motion':motion,'transition':transition,
                      'sfx':sfx,'beat_aligned':abs(end-_nearest_beat(end,beats,.08))<.01})
    mood='neutral_punch' if (bpm or 0)>=105 else 'warm_cinematic'
    return {'version':6,'director':'local_creative_director','target_seconds':target,'tempo_bpm':bpm,
            'grade_mood':mood,'music_strategy':{'cut_to_beats':True,'duck_under_speech':True,'target_lufs':-14},
            'edits':edits,'creative_policy':{'hook_first':True,'preserve_chronology':True,'max_effect_density':'medium',
            'speed_range':[.88,1.18],'transitions':'prefer_cuts_over_gimmicks'},
            'notes':['V6 ranks scenes using timing, beat and V5 visual geometry; semantic story judgment still belongs to a multimodal/LLM pass.',
                     'transition and sfx fields are creative intents; hard/beat cuts render natively, external SFX assets require an overlay/audio pass.']}


def apply_to_edl(edl, plan):
    out=dict(edl); out['ranges']=[]
    for e in plan['edits']:
        out['ranges'].append({'source':e['source'],'start':e['start'],'end':e['end'],'beat':e['role'].upper(),
                              'speed':e['speed'],'motion':e['motion'],'transition':e['transition'],'sfx':e['sfx'],
                              'creative_score':e['score']})
    out['grade']=plan['grade_mood']; out.setdefault('short_form',{})['beat_sync']=True
    out['creative_director']={'version':6,'name':plan['director'],'music_strategy':plan['music_strategy'],
                              'policy':plan['creative_policy']}
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('analysis',type=Path); ap.add_argument('-o','--output',type=Path)
    ap.add_argument('--director',type=Path); ap.add_argument('--edl',type=Path); ap.add_argument('--apply',action='store_true')
    ap.add_argument('--target',type=float,default=20.0); a=ap.parse_args()
    analysis=json.loads(a.analysis.read_text()); director=json.loads(a.director.read_text()) if a.director else None
    plan=build_plan(analysis,director,a.target); out=a.output or a.analysis.with_name('creative.v6.json')
    out.write_text(json.dumps(plan,ensure_ascii=False,indent=2)); print(f'wrote {out} | {len(plan["edits"])} creative edits')
    if a.edl and a.apply:
        edl=json.loads(a.edl.read_text()); a.edl.write_text(json.dumps(apply_to_edl(edl,plan),ensure_ascii=False,indent=2)); print(f'applied V6 creative plan → {a.edl}')
if __name__=='__main__': main()
