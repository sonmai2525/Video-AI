import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helpers'))
from creative_director_v14 import apply

def base():
 return {'story_v13':{'type':'process'},'ranges':[{'start':0,'end':.4,'beat':'TEASER'},{'start':1,'end':4,'v131_visual_progress':.1},{'start':4,'end':8,'v131_visual_progress':.7},{'start':8,'end':12,'v131_visual_progress':.5},{'start':12,'end':16,'beat':'PAYOFF'}]}
def test_voice_is_sparse_and_story_aware():
 x=apply(base(),20); assert 1<=len(x['voice_plan_v14']['events'])<=3; assert x['voice_plan_v14']['language']=='vi'
def test_payoff_is_clean():
 x=apply(base(),20); assert x['ranges'][-1]['motion']=='none'; assert x['ranges'][-1]['v14_role']=='reward'
def test_stagnant_ranges_speed_up():
 x=apply(base(),20); assert x['ranges'][1]['speed']>1
def test_no_voice_for_short_unknown_clip():
 x=apply({'story_v13':{'type':'unknown'},'ranges':[{'start':0,'end':5}]},5); assert x['voice_plan_v14']['events']==[]
