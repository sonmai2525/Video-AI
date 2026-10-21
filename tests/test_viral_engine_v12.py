from helpers.viral_engine_v12 import build_candidates,apply

def test_v12_selects_candidate_and_hook():
    ed={'ranges':[{'start':0,'end':2,'speed':1},{'start':4,'end':6,'speed':1},{'start':8,'end':10,'speed':1}]}
    an={'scenes':[{'start':0,'end':2,'motion_score':.1},{'start':4,'end':6,'motion_score':.95},{'start':8,'end':10,'motion_score':.4}]}
    p=build_candidates(ed,an,6)
    assert len(p['candidates'])==3 and p['winner']
    out=apply(ed,p)
    assert out['ranges'][0]['beat']=='HOOK'
    assert out['viral_v12']['winner']==p['winner']
