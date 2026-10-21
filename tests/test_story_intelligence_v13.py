from helpers.story_intelligence_v13 import protect_process,critique
def test_process_payoff_is_brief_teaser_then_final():
 ed={'ranges':[{'source':'x','start':0,'end':3},{'source':'x','start':8,'end':11},{'source':'x','start':20,'end':24},{'source':'x','start':32,'end':36}]}; out=protect_process(ed,20); assert out[0]['v13_payoff_teaser']; assert out[0]['end']-out[0]['start']<=.56; assert out[-1]['v13_payoff_protected']; assert [r['start'] for r in out[1:-1]]==sorted(r['start'] for r in out[1:-1])
def test_critic_rejects_reversed_process():
 rep=critique({'ranges':[{'start':20,'end':22},{'start':2,'end':4},{'start':6,'end':8}]},{'type':'process'}); assert not rep['pass']; assert any(x['code']=='BROKEN_PROCESS_ORDER' for x in rep['issues'])
