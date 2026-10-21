import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helpers'))
from multimodal_story_v10 import apply

def test_v10_puts_hook_first_and_payoff_last():
    edl={'ranges':[{'source':'main','start':0,'end':1},{'source':'main','start':1,'end':2},{'source':'main','start':2,'end':3}]}
    plan={'director':'multimodal_story_v10','hook_scene_id':1,'payoff_scene_id':2,'vlm_enriched':True,'scenes':[
      {'scene_id':0,'start':0,'end':1,'story_score':.3,'narrative_role':'support','focus_x':.5,'focus_y':.5,'tracking_mode':'locked','headline':''},
      {'scene_id':1,'start':1,'end':2,'story_score':.9,'narrative_role':'hook','focus_x':.3,'focus_y':.5,'tracking_mode':'follow','headline':'WOW'},
      {'scene_id':2,'start':2,'end':3,'story_score':.8,'narrative_role':'payoff','focus_x':.6,'focus_y':.5,'tracking_mode':'locked','headline':'END'}]}
    out=apply(edl,plan,20)
    assert [r['scene_id'] for r in out['ranges']]==[1,0,2]
    assert out['ranges'][0]['beat']=='HOOK' and out['ranges'][-1]['beat']=='PAYOFF'
    assert out['multimodal_story_v10']['vlm_enriched'] is True
