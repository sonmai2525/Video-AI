import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/'helpers'/'creative_director.py'
spec=importlib.util.spec_from_file_location('creative_director',P); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def sample():
    return {'scenes':[{'id':0,'start':0,'end':1.2,'duration':1.2},{'id':1,'start':1.2,'end':4.2,'duration':3.0},{'id':2,'start':4.2,'end':5.4,'duration':1.2}], 'audio':{'beats':[1.2,2.0,3.0,4.2,5.4],'tempo_bpm':120}}

def test_v6_plan_has_creative_fields():
    p=m.build_plan(sample(),target=5)
    assert p['version']==6 and p['edits']
    assert {'speed','motion','transition','role','score'} <= set(p['edits'][0])
    assert p['edits'][0]['role']=='hook'

def test_apply_replaces_ranges_and_keeps_v6_metadata():
    p=m.build_plan(sample(),target=5); e=m.apply_to_edl({'ranges':[],'short_form':{}},p)
    assert e['ranges'][0]['speed']>0
    assert e['creative_director']['version']==6
    assert e['short_form']['beat_sync'] is True
