from helpers.creative_director_v15 import apply

def sample():
 return {'story_v13':{'type':'process'},'ranges':[{'start':0,'end':.8,'speed':1,'beat':'TEASER','v131_visual_progress':.8},{'start':1,'end':5,'speed':1,'beat':'BUILD','v131_visual_progress':.1},{'start':5,'end':9,'speed':1,'beat':'DETAIL','v131_visual_progress':.7},{'start':9,'end':12,'speed':1,'beat':'PAYOFF','v131_visual_progress':.8}]}

def test_v15_fixes_all_below8_categories():
 o=apply(sample()); f=o['creative_director_v15']; assert set(f['v14_below_8_fixes'])=={'hook','caption','dynamic_editing','voice_audio'}
 assert o['voice_plan_v15']['events']; assert o['v15_text_cards']; assert o['v15_audio_direction']['real_tts']

def test_teaser_short_and_dynamic():
 o=apply(sample()); r=o['ranges'][0]; assert r['end']-r['start']<=.39; assert r['motion']=='punch_in'

def test_low_progress_compressed_payoff_clean():
 o=apply(sample()); assert o['ranges'][1]['speed']>1; assert o['ranges'][-1]['motion']=='none'
