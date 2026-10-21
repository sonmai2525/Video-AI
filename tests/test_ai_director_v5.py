import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helpers'))
from ai_director import inspect_frame, apply_to_edl, near_beat

def test_negative_space_prefers_less_busy_area():
    img=np.zeros((640,360,3),dtype=np.uint8)
    # make right side very busy, left side remains empty
    for x in range(190,360,8): img[:,x:x+3]=255
    r=inspect_frame(img)
    assert r['layout'] in {'left','top_left','upper','lower_safe'}
    assert r['scores']['left'] < r['scores']['right']

def test_apply_director_plan():
    edl={'ranges':[]}; plan={'director':'local_visual_director','policy':{},'visual_text_events':[{'start':0,'end':1,'layout':'upper'}]}
    out=apply_to_edl(edl,plan)
    assert out['caption_style']=='visual_dynamic'
    assert out['visual_text_events'][0]['layout']=='upper'
    assert out['director']['version']==5

def test_near_beat():
    assert near_beat(1.05,[1.0,2.0])
    assert not near_beat(1.3,[1.0,2.0])
