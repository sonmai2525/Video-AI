"""Generate synchronized motion-caption cards for required TTS narration."""
import json, math
from pathlib import Path

def ensure_narration_plan(edl_path,script_path=None):
    p=Path(edl_path);ed=json.loads(p.read_text(encoding='utf-8'))
    duration=sum(max(0,(float(r['end'])-float(r['start']))/max(.01,float(r.get('speed',1)))) for r in ed.get('ranges',[]))
    plan=ed.get('voice_plan_v15') or {}
    if script_path:
        lines=[x.strip() for x in Path(script_path).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
        if not lines:raise ValueError('Voice script is empty')
        # Spread sentences across available video; cap word length to avoid hard TTS cuts.
        spacing=max(.8,duration/max(1,len(lines)))
        events=[{'at':round(i*spacing+.08,2),'max_seconds':max(.35,min(spacing-.12,duration-i*spacing-.12)),'text':line} for i,line in enumerate(lines) if i*spacing+.08<duration]
    else:
        events=plan.get('events') or []
        # Existing V15 voice events can be empty for unidentified story types.
        # Avoid publishing a fake AI-read video if an actual script cannot be derived.
    plan.update({'enabled':bool(events),'voice':plan.get('voice','vi-VN-HoaiMyNeural'),'rate':plan.get('rate','+4%'),'volume':plan.get('volume','+0%'),'duck_music_db':plan.get('duck_music_db',-12),'events':events})
    ed['voice_plan_v15']=plan
    if events:
        ed['v15_text_cards']=[]
        # Text timing must match VO start and end; words animate sequentially with ASS karaoke tags.
        ed['v19_voice_caption_events']=[{'start':e['at'],'end':min(duration,e['at']+e['max_seconds']),'text':e['text']} for e in events]
    p.write_text(json.dumps(ed,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'events':len(events),'duration':round(duration,2),'source':'script' if script_path else 'v15_existing'}
