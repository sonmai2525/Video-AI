import importlib.util, json, tempfile
from pathlib import Path
MODULE_PATH=Path(__file__).parents[1]/"helpers"/"render.py"
SPEC=importlib.util.spec_from_file_location("video_use_render_v4",MODULE_PATH)
render=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(render)

def test_v4_layout_motion():
    assert r"\move" in render._v4_layout_tag({"layout":"upper","motion":"rise"},0)
    assert r"\pos" in render._v4_layout_tag({"x":.25,"y":.3},0)

def test_v4_event_and_ass():
    with tempfile.TemporaryDirectory() as d:
        edit=Path(d); (edit/"transcripts").mkdir()
        (edit/"transcripts"/"main.json").write_text(json.dumps({"words":[
          {"type":"word","text":"watch","start":0,"end":.3},
          {"type":"word","text":"this","start":.31,"end":.6}
        ]}))
        edl={"sources":{"main":"main.mp4"},"ranges":[{"source":"main","start":0,"end":1}],
             "visual_text_events":[{"start":0,"end":1,"layout":"upper","motion":"rise","style":"hook","icon":"!"}]}
        out=edit/"v4.ass"; render.build_master_ass_v4(edl,edit,out,"visual_dynamic")
        text=out.read_text()
        assert "v4-hook" in text and r"\move" in text and "!" in text
