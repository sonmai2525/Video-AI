from helpers.story_intelligence_v131 import apply

def test_nonprocess_keeps_ranges():
    ed={'ranges':[{'start':0,'end':2,'speed':1}], 'story_v13':{'type':'general'}}
    out=apply(ed,'missing.mp4',20)
    assert out['ranges']==ed['ranges']
    assert out['finish_director_v131']['version']=='13.1'

def test_process_micro_hook_without_video():
    ed={'ranges':[{'start':9,'end':10,'speed':1,'beat':'TEASER','v13_payoff_teaser':True},{'start':0,'end':1,'speed':1},{'start':8,'end':10,'speed':1,'beat':'PAYOFF'}], 'story_v13':{'type':'process'}}
    out=apply(ed,'missing.mp4',20)
    assert out['ranges'][0]['end']-out['ranges'][0]['start'] <= .401
    assert out['ranges'][-1]['motion']=='none'
    assert out['v131_caption_policy']['max_cards']==3
