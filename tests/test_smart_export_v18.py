import unittest, tempfile, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'helpers'))
from smart_export_v18 import verify_mp4, publish_mp4, ExportError
class TestSmartExport(unittest.TestCase):
    def test_missing_fails(self):
        with self.assertRaises(ExportError): verify_mp4('/nonexistent/example_video.mp4')
    def test_atomic_valid_copy(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.mp4'; q=Path(d)/'OUTPUT'/'output.mp4'
            p.write_bytes(b'0'*2048)
            with patch('smart_export_v18.verify_mp4',return_value={'duration_seconds':2,'width':100,'height':200}):
                r=publish_mp4(p,q)
            self.assertEqual(p.read_bytes(),q.read_bytes())
            self.assertEqual(r['file'],str(q.resolve()))
            self.assertFalse((q.parent/'output.export-partial.mp4').exists())
    def test_atomic_failure_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.mp4'; q=Path(d)/'output.mp4'; p.write_bytes(b'1'*2048);q.write_bytes(b'OLD')
            with patch('smart_export_v18.verify_mp4',side_effect=ExportError('invalid')):
                with self.assertRaises(ExportError):publish_mp4(p,q)
            self.assertEqual(q.read_bytes(),b'OLD')
