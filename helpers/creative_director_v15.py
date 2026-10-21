"""V15 Creative Director — fixes V14 weak spots: hook, typography, dynamic shots and real voice handoff."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def dur(r): return max(.01,(float(r['end'])-float(r['start']))/max(.01,float(r.get('speed',1))))

def apply(edl,target=20.0):
    out=dict(edl); rs=[dict(r) for r in out.get('ranges',[])]; story=out.get('story_v13') or {}; typ=story.get('type','unknown')
    total=sum(dur(r) for r in rs)
    # Hook 3.0: teaser must be brief and visually different, never a long spoiler.
    teaser_seen=False; elapsed=0.0; transforms=0
    for i,r in enumerate(rs):
        beat=str(r.get('beat','')).upper(); p=float(r.get('v131_visual_progress',.35)); d=dur(r)
        if beat=='TEASER' and not teaser_seen:
            # cap source duration so rendered teaser is roughly 0.28-0.42 s
            srcd=float(r['end'])-float(r['start']); cap=min(srcd,.38*max(.01,float(r.get('speed',1))))
            r['end']=float(r['start'])+max(.24,cap); r['motion']='punch_in'; r['v15_role']='micro_promise'; teaser_seen=True
        elif beat=='PAYOFF':
            r['motion']='none'; r['speed']=min(1.0,float(r.get('speed',1))); r['v15_role']='clean_reward'
        else:
            # Shot Transformation Director: visible rhythm, but capped to avoid template spam.
            if p < .16:
                r['speed']=min(1.75,max(1.18,float(r.get('speed',1))*1.24)); r['motion']='none'; r['v15_role']='compress'
            elif p > .52 and elapsed>1.8 and transforms<4:
                r['motion']='punch_in' if transforms%2==0 else 'push_out'; r['v15_role']='detail_emphasis'; transforms+=1
            elif p > .34 and transforms<4 and i%3==1:
                r['motion']='zoom_in'; transforms+=1
            else: r['motion']='none'
        elapsed+=d
    out['ranges']=rs
    # Voice script: shorter than V14 and written to complement visuals, not narrate them.
    events=[]
    if typ in ('process','transformation','story','tutorial') and total>=8:
        events=[
          {'at':.18,'max_seconds':1.85,'role':'hook','text':'Nhìn mấy nét đầu này... bạn đoán sẽ thành gì?'},
          {'at':max(4.0,total*.38),'max_seconds':1.65,'role':'progress','text':'Đến đây mới bắt đầu thấy rõ rồi.'},
          {'at':max(8.0,total-2.8),'max_seconds':1.35,'role':'payoff','text':'Và đây là kết quả.'}
        ]
    out['voice_plan_v15']={'enabled':'auto','language':'vi-VN','voice':'vi-VN-HoaiMyNeural','rate':'+4%','volume':'+0%','duck_music_db':-10,'max_lines':3,'events':events}
    # Motion typography: synthetic cards; text is deliberately NOT a transcript of voice.
    cards=[]
    if events:
        cards=[
          {'start':.12,'end':1.25,'text':'MẤY NÉT ĐẦU...','style':'hook','layout':'upper','motion':'rise','box':True},
          {'start':max(4.0,total*.38),'end':max(4.0,total*.38)+1.05,'text':'BẮT ĐẦU THẤY RỒI','style':'emphasis','layout':'lower_safe','motion':'pop','box':False},
          {'start':max(8.0,total-2.5),'end':max(8.0,total-1.25),'text':'KẾT QUẢ','style':'emotion','layout':'upper','motion':'rise','box':False}
        ]
    out['v15_text_cards']=cards
    out['v15_audio_direction']={'real_tts':True,'duck_under_voice_db':-10,'music_build_before_payoff':True,'voice_priority':True}
    out['creative_director_v15']={'version':'15.0','hook_3':True,'shot_transformation':True,'motion_typography':True,'real_tts_renderer':True,'v14_below_8_fixes':['hook','caption','dynamic_editing','voice_audio'],'effect_spam_guard':True}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('edl',type=Path); ap.add_argument('-o','--output',type=Path,required=True); ap.add_argument('--target',type=float,default=20); ap.add_argument('--apply',action='store_true'); a=ap.parse_args()
    ed=json.loads(a.edl.read_text()); out=apply(ed,a.target); report={k:out.get(k) for k in ('creative_director_v15','voice_plan_v15','v15_text_cards','v15_audio_direction')}; a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if a.apply:a.edl.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('V15 creative director applied')
if __name__=='__main__':main()
