import unittest
from helpers.chatgpt_export_v21 import parse_boxes, captions

class TestChatGPTExportV21(unittest.TestCase):
    def test_boxes(self):
        self.assertEqual(parse_boxes('1,2,4,5;6,7,8,9',100,100),[[1,2,4,5],[6,7,8,9]])
    def test_bad_box(self):
        with self.assertRaises(ValueError): parse_boxes('1,2,90,90',100,100)
    def test_animated_subs(self):
        s=captions('Một hai ba bốn năm sáu',4,720,1280)
        self.assertIn('\\k',s)
        self.assertEqual(s.count('Dialogue:'),2)
    def test_empty_script(self):
        with self.assertRaises(ValueError): captions(' ',4,720,1280)
