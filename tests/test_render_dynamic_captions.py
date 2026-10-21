import importlib.util, json, tempfile
from pathlib import Path
MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render_dynamic", MODULE_PATH)
render = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(render)

def test_dynamic_ass_contains_animation_and_karaoke():
    with tempfile.TemporaryDirectory() as d:
        edit=Path(d); (edit/"transcripts").mkdir()
        (edit/"transcripts"/"main.json").write_text(json.dumps({"words":[
            {"type":"word","text":"hello","start":1.0,"end":1.3},
            {"type":"word","text":"world","start":1.32,"end":1.7}
        ]}))
        edl={"sources":{"main":"main.mp4"},"ranges":[{"source":"main","start":0.9,"end":2.0}]}
        out=edit/"master.ass"; render.build_master_ass(edl,edit,out,"viral_pop")
        text=out.read_text()
        assert "[V4+ Styles]" in text
        assert r"\kf" in text
        assert r"\fscx72" in text
        assert "HELLO" in text and "WORLD" in text

def test_all_presets_exist():
    assert {"viral_pop","punch","clean","cinematic"}.issubset(render.CAPTION_PRESETS)
