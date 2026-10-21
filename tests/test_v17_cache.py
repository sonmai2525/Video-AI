import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helpers'))
from analysis_cache_v17 import key_for,analyze_cached

class AnalysisCacheV17Tests(unittest.TestCase):
    def test_cache_key_changes_with_input_and_settings(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sample.mp4';p.write_bytes(b'a'*100000)
            original=key_for(p,True,.30)
            self.assertNotEqual(original,key_for(p,False,.30))
            self.assertNotEqual(original,key_for(p,True,.40))
            p.write_bytes(b'b'*100000)
            self.assertNotEqual(original,key_for(p,True,.30))

    def test_cache_hit_skips_analysis(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sample.mp4';p.write_bytes(b'test bytes')
            output=Path(d)/'analysis.json';cache=Path(d)/'cache';cache.mkdir()
            name=key_for(p,True,.3)
            (cache/(name+'.json')).write_text('{"source":"'+str(p.resolve()).replace('\\','\\\\')+'","scenes":[],"metadata":{}}')
            hit=analyze_cached(p,output,quick=True,cache_dir=cache)
            self.assertTrue(hit)
            self.assertIn('scenes',output.read_text())
