"""V14 Creative Director: visible creative delta, voice plan, dynamic pacing and payoff build-up."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path

def dur(r): return max(.01,(float(r['end'])-float(r['start']))/max(.01,float(r.get('speed',1))))
def apply(edl,target=20.0):
    out=dict(edl); rs=[dict(r) for r in out.get('ranges',[])]; story=out.get('story_v13') or {}; typ=story.get('type','unknown')
    # Deliberately create visible rhythm changes without effect spam.
    t=0.; interrupts=0
    for i,r in enumerate(rs):
        d=dur(r); beat=r.get('beat','')
        if beat=='TEASER':
            r['motion']='zoom_in'; r['v14_role']='promise'; r['speed']=max(1.0,float(r.get('speed',1)))
        elif beat=='PAYOFF':
            r['motion']='none'; r['v14_role']='reward'; r['speed']=min(1.0,float(r.get('speed',1)))
        else:
            p=float(r.get('v131_visual_progress',.35))
            if p<.18: r['speed']=min(1.55,max(1.12,float(r.get('speed',1))*1.18)); r['motion']='none'
            elif p>.48 and interrupts<3 and t>2.2:
                r['motion']='zoom_in' if interrupts%2==0 else 'zoom_out'; r['v14_emphasis']=True; interrupts+=1
            elif i%3==1: r['motion']='none'
        t+=d
    out['ranges']=rs
    # Voice is planned, not forced. Renderer/TTS integration can consume this plan.
    voice=[]
    total=sum(dur(r) for r in rs)
    if typ in ('process','transformation','story','tutorial') and total>=8:
        voice=[
          {'at':.15,'max_seconds':2.2,'role':'hook','text':'Nhìn những nét đầu tiên này... bạn đoán kết quả sẽ ra sao?'},
          {'at':max(4.2,total*.36),'max_seconds':2.0,'role':'progress','text':'Đến đây, bức tranh mới thật sự bắt đầu có hồn.'},
          {'at':max(9.0,total-3.1),'max_seconds':1.7,'role':'payoff','text':'Và đây là kết quả cuối cùng.'}
        ]
    out['voice_plan_v14']={'enabled':'auto','language':'vi','max_lines':3,'duck_music_db':-8,'events':voice,'policy':'voice only when it adds story; never narrate every visible action'}
    out['v14_caption_policy']={'coordinate_with_voice':True,'do_not_duplicate_voice':True,'keyword_only_when_voice':True,'max_words_on_voice_card':5,'max_cards':3}
    out['v14_audio_direction']={'build_before_payoff_seconds':1.0,'payoff_breathe_seconds':1.7,'duck_under_voice_db':-8,'avoid_constant_high_energy':True}
    out['creative_director_v14']={'version':'14.0','visible_delta_required':True,'dynamic_editing':True,'voice_director':True,'hook_2':True,'payoff_2':True,'effect_spam_guard':True}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('edl',type=Path); ap.add_argument('-o','--output',type=Path,required=True); ap.add_argument('--target',type=float,default=20); ap.add_argument('--apply',action='store_true'); a=ap.parse_args()
    ed=json.loads(a.edl.read_text()); out=apply(ed,a.target); report={k:out.get(k) for k in ('creative_director_v14','voice_plan_v14','v14_caption_policy','v14_audio_direction')}; a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2));
    if a.apply:a.edl.write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print('V14 creative director applied:',json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
