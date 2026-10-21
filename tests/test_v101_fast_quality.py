import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wm',ROOT/'helpers'/'watermark_cleanup.py'); wm=importlib.util.module_from_spec(spec); spec.loader.exec_module(wm)
def test_edge_crop_prefers_top_for_small_top_logo():
    c=wm.edge_crop(1920,1080,[100,0,240,60],.12)
    assert c and c[0]=='top' and c[1] < .12
def test_interior_logo_is_not_destructively_cropped():
    assert wm.edge_crop(1920,1080,[800,400,240,80],.12) is None
