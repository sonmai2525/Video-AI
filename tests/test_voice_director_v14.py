from pathlib import Path
import json,subprocess,sys

def test_voice_export(tmp_path):
 ed=tmp_path/'e.json'; out=tmp_path/'v.json'; ed.write_text(json.dumps({'voice_plan_v14':{'language':'vi','events':[{'at':0.2,'max_seconds':1.5,'text':'Xin chào'}]}}))
 subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'helpers'/'voice_director_v14.py'),str(ed),'-o',str(out)],check=True)
 assert json.loads(out.read_text())['events'][0]['text']=='Xin chào'; assert out.with_suffix('.srt').exists()
