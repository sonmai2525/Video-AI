import importlib.util, json, tempfile
from pathlib import Path
MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render_v3", MODULE_PATH)
render = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(render)

def test_semantic_roles():
    assert render._semantic_role("WAIT FOR THIS",0,4) == "hook"
    assert render._semantic_role("SAVE 50%",2,4) == "number"
    assert render._semantic_role("FOLLOW FOR MORE",3,4) == "cta"

def test_auto_dynamic_and_override():
    with tempfile.TemporaryDirectory() as d:
        edit=Path(d); (edit/"transcripts").mkdir()
        (edit/"transcripts"/"main.json").write_text(json.dumps({"words":[
            {"type":"word","text":"wait","start":0.0,"end":0.25},
            {"type":"word","text":"here","start":0.26,"end":0.55},
            {"type":"word","text":"50%","start":0.8,"end":1.1},
            {"type":"word","text":"off","start":1.12,"end":1.4}
        ]}))
        edl={"sources":{"main":"main.mp4"},"ranges":[{"source":"main","start":0,"end":1.5}],
             "caption_events":[{"start":0,"end":0.6,"role":"emphasis"}]}
        out=edit/"master.ass"; render.build_master_ass(edl,edit,out,"auto_dynamic")
        text=out.read_text()
        assert "Dialogue:" in text
        assert ",emphasis,emphasis," in text
        assert ",number,number," in text
        assert r"\kf" in text
