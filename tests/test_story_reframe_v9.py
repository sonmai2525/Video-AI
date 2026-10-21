import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helpers'))
from story_reframe_v9 import apply

def test_apply_adds_focus_and_story_fields():
    edl={'ranges':[{'source':'main','start':0.0,'end':1.0,'scene_id':0,'motion':'none'}]}
    plan={'director':'story_reframe_v9','scenes':[{'scene_id':0,'start':0,'end':1,'focus_x':.25,'focus_y':.5,'tracking_mode':'locked','moment_score':.75,'story_role':'hook_candidate'}]}
    out=apply(edl,plan); r=out['ranges'][0]
    assert r['focus_x']==.25 and r['moment_score']==.75
    assert r['motion']=='zoom_in'
    assert out['story_reframe_v9']['version']==9
