"""Build Turbo's lightweight EDL, director, creative and viral plans in one Python process."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from ai_director import direct,apply_to_edl as apply_visual
from creative_director import build_plan,apply_to_edl as apply_creative
from viral_engine_v12 import build_candidates,apply as apply_viral
from creative_director_v15 import apply as apply_v15

def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def build(video,analysis_path,work,target,aspect):
    an=json.loads(analysis_path.read_text(encoding='utf-8'))
    scenes=an.get('scenes') or []; ranges=[];elapsed=0.
    for s in scenes:
        if elapsed>=target:break
        a=float(s['start']);dur=min(float(s['duration']),3.5,target-elapsed)
        if dur<.25:continue
        ranges.append({'source':'main','start':round(a,3),'end':round(a+dur,3),'beat':'VISUAL'});elapsed+=dur
    ed={'version':2,'sources':{'main':an['source']},'ranges':ranges,'grade':'auto','output':{'aspect':aspect,'crop_mode':'center'},'short_form':{'target_seconds':target,'beat_sync':True,'safe_zones':True},'overlays':[]}
    director=direct(video,an);write(work/'director.v5.json',director);ed=apply_visual(ed,director)
    creative=build_plan(an,director,target);write(work/'creative.v6.json',creative);ed=apply_creative(ed,creative)
    viral=build_candidates(ed,an,target);write(work/'viral.v12.json',viral);ed=apply_viral(ed,viral)
    ed=apply_v15(ed,target);write(work/'creative.v15.json',{k:ed.get(k) for k in ('creative_director_v15','voice_plan_v15','v15_text_cards','v15_audio_direction')})
    write(work/'edl.json',ed)
    return viral

def main():
    p=argparse.ArgumentParser();p.add_argument('video',type=Path);p.add_argument('analysis',type=Path);p.add_argument('work',type=Path);p.add_argument('--target',type=float,default=20.);p.add_argument('--aspect',default='9:16');a=p.parse_args()
    a.work.mkdir(parents=True,exist_ok=True);v=build(a.video,a.analysis,a.work,a.target,a.aspect)
    print('Turbo V17: one planning process; chosen',v.get('winner'))
if __name__=='__main__':main()
