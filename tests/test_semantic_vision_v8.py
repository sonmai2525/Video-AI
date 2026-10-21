import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'helpers'))
from semantic_vision_director import apply

def test_apply_v8_enriches_edl():
    edl={'visual_text_events':[{'start':0,'end':1,'layout':'center','motion':'drift'}],'clips':[{'start':0,'end':1}]}
    plan={'director':'semantic_vision_director','scenes':[{'start':0,'end':1,'safe_text_layout':'left','subject_region':'right','confidence':.8,'action_level':'high','shot_scale':'medium','semantic_tags':['person']}]}
    got=apply(edl,plan)
    assert got['director_v8']['version']==8
    assert got['visual_text_events'][0]['layout']=='left'
    assert got['visual_text_events'][0]['motion']=='pop'
    assert got['clips'][0]['semantic_tags']==['person']
