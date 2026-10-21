"""V14 voice director. Creates a TTS-ready script/SRT plan without requiring a paid provider."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def ts(x):
    ms=int(round(float(x)*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000); return f'{h:02}:{m:02}:{s:02},{ms:03}'
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('edl',type=Path); ap.add_argument('-o','--output',type=Path,required=True); a=ap.parse_args(); ed=json.loads(a.edl.read_text()); plan=ed.get('voice_plan_v14') or {}; ev=plan.get('events') or []
    data={'version':'14.0','provider':'external_or_local_tts','language':plan.get('language','vi'),'duck_music_db':plan.get('duck_music_db',-8),'events':ev}; a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    s=[]
    for i,e in enumerate(ev,1):
        st=float(e['at']); en=st+float(e.get('max_seconds',2)); s += [str(i),f'{ts(st)} --> {ts(en)}',e['text'],'']
    a.output.with_suffix('.srt').write_text('\n'.join(s),encoding='utf-8'); print(f'V14 voice plan: {len(ev)} lines')
if __name__=='__main__':main()
