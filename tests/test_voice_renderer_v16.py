import json, subprocess
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helpers'))
from voice_renderer_v16 import valid_events, mix, probe

def test_events_boundaries_and_overlap():
    events=valid_events([{'at':4,'max_seconds':4,'text':'last'}, {'at':1,'max_seconds':8,'text':'first'}, {'at':100,'text':'late'}, {'at':-1,'text':'early'}, {'at':2,'text':''}], 6)
    assert len(events)==2
    assert events[0]['max_seconds'] <= 2.95
    assert events[1]['max_seconds']==2

def test_silent_video_no_voice_event(tmp_path):
    src=tmp_path/'src.mp4'; out=tmp_path/'out.mp4'; edl=tmp_path/'edl.json'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','lavfi','-i','color=c=blue:s=320x240:r=24','-t','1','-c:v','mpeg4',str(src)],check=True)
    edl.write_text(json.dumps({'voice_plan_v15':{'events':[]}}))
    rep=mix(src,edl,out)
    assert rep['status']=='no_voice_events'
    assert out.exists() and probe(out)[0]>.8
