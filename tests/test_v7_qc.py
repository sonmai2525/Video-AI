import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helpers'))
from viral_qc import repair

def test_repair_removes_tiny_and_clamps_speed():
    edl={'ranges':[{'source':'main','start':0,'end':.1,'speed':1},{'source':'main','start':1,'end':2,'speed':1.5,'motion':'zoom_in'}]}
    out=repair(edl,{'score':70,'issues':[{'code':'extreme_speed'},{'code':'effect_density'}]})
    assert len(out['ranges'])==1 and out['ranges'][0]['speed']==1.22

def test_repair_low_confidence_text():
    edl={'ranges':[],'visual_text_events':[{'confidence':.2,'layout':'center','motion':'shake'}]}
    out=repair(edl,{'score':70,'issues':[{'code':'low_text_confidence'}]})
    e=out['visual_text_events'][0]; assert e['layout']=='upper' and e['style']=='clean'
