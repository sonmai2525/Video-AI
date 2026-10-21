"""V16 Auto Viral Editor — retention-first, fast/smart/max.

Fast-quality preserves a good source edit and spends compute where viewers notice it:
scene/beat analysis, concise EDL, visual text, light creative motion, render and one QC.
Full-ai keeps the V5→V10 semantic/story pipeline.
"""
from __future__ import annotations
import argparse,json,shutil,subprocess,sys,time
from pathlib import Path
from viral_qc import evaluate,repair
from watermark_cleanup import clean as clean_watermark, parse_box
from analysis_cache_v17 import analyze_cached
from smart_export_v18 import verify_mp4, publish_mp4, ExportError

def run(cmd):
    print('>',' '.join(map(str,cmd))); subprocess.run(list(map(str,cmd)),check=True)

def main():
    ap=argparse.ArgumentParser(description='V17 one-command retention-first short-form editor')
    ap.add_argument('video',type=Path); ap.add_argument('-o','--output',type=Path,required=True)
    ap.add_argument('--target',type=float,default=20); ap.add_argument('--aspect',choices=['9:16','16:9','1:1','source'],default='9:16')
    ap.add_argument('--mode',choices=['turbo','fast','smart','max','fast-quality','full-ai'],default='smart')
    ap.add_argument('--no-cache',action='store_true',help='Force fresh analysis'); ap.add_argument('--cache-dir',type=Path,help='Analysis cache directory'); ap.add_argument('--workdir',type=Path); ap.add_argument('--caption-style',default='visual_dynamic'); ap.add_argument('--preview',action='store_true'); ap.add_argument('--no-subtitles',action='store_true'); ap.add_argument('--no-auto-repair',action='store_true')
    ap.add_argument('--voice-script',type=Path,help='Vietnamese narration text, one line per scene; UTF-8')
    ap.add_argument('--allow-no-voice',action='store_true',help='Allow export without narration explicitly')
    ap.add_argument('--watermark-box',help='optional x,y,w,h pixels; edge marks are cropped cleanly, never blurred'); ap.add_argument('--max-watermark-crop',type=float,default=.12)
    a=ap.parse_args(); started=time.time();
    if a.mode=='fast-quality': a.mode='fast'
    if a.mode=='full-ai': a.mode='max'
    original=a.video.resolve(); output=a.output.resolve(); root=Path(__file__).resolve().parent; work=(a.workdir or output.parent/(output.stem+'_v17')).resolve(); work.mkdir(parents=True,exist_ok=True)
    video=original; wm_report=None
    if a.watermark_box:
        cleaned=work/'source.clean.mp4'; wm_report=clean_watermark(original,cleaned,parse_box(a.watermark_box),'auto',a.max_watermark_crop); (work/'watermark.json').write_text(json.dumps(wm_report,ensure_ascii=False,indent=2)); video=cleaned if wm_report.get('applied') else original
        print('watermark:',wm_report.get('method'),wm_report.get('reason',''))
    analysis=work/'analysis.json'; edl=work/'edl.json'; first=work/'first_pass.mp4'; qc1=work/'qc.first.json'
    analyze_cmd=[sys.executable,root/'analyze_short.py',video,'-o',analysis]
    if a.mode=='turbo': analyze_cmd.append('--quick')
    cache_hit=analyze_cached(video,analysis,quick=a.mode=='turbo',cache_dir=a.cache_dir,no_cache=a.no_cache)
    print('Analysis cache:', 'HIT' if cache_hit else 'MISS')
    if a.mode!='turbo':run([sys.executable,root/'make_short_edl.py',analysis,'-o',edl,'--target',a.target,'--aspect',a.aspect])
    if a.mode=='turbo':
        run([sys.executable,root/'turbo_plan_v17.py',video,analysis,work,'--target',a.target,'--aspect',a.aspect])
    elif a.mode=='fast':
        # One visual pass + one light creative pass. Skip V8/V9/V10 storyboard generation.
        visual=work/'director.v5.json'; creative=work/'creative.v6.json'
        run([sys.executable,root/'ai_director.py',video,analysis,'-o',visual,'--edl',edl,'--apply'])
        run([sys.executable,root/'creative_director.py',analysis,'-o',creative,'--director',visual,'--edl',edl,'--apply','--target',a.target])
    else:
        visual=work/'director.v5.json'; creative=work/'creative.v6.json'; semantic=work/'semantic.v8.json'; story=work/'story.v9.json'
        run([sys.executable,root/'ai_director.py',video,analysis,'-o',visual,'--edl',edl,'--apply'])
        run([sys.executable,root/'creative_director.py',analysis,'-o',creative,'--director',visual,'--edl',edl,'--apply','--target',a.target])
        run([sys.executable,root/'semantic_vision_director.py',video,analysis,'-o',semantic,'--edl',edl,'--apply'])
        run([sys.executable,root/'story_reframe_v9.py',video,analysis,'-o',story,'--semantic',semantic,'--edl',edl,'--apply'])
        if a.mode=='max':
            story10=work/'story.v10.json'
            run([sys.executable,root/'multimodal_story_v10.py',video,analysis,story,'-o',story10,'--semantic',semantic,'--assets-dir',work/'v10_storyboards','--edl',edl,'--apply','--target',a.target])
    # Turbo: only effective core stages. The V13/V13.1 reports and V14 plan
    # are optional for this profile; V15 provides motion + narration directly.
    viral12=work/'viral.v12.json'
    if a.mode!='turbo':run([sys.executable,root/'viral_engine_v12.py',analysis,edl,'-o',viral12,'--target',a.target,'--apply'])
    story13=finish131=creative14=voice14=None
    if a.mode!='turbo':
        story13=work/'story.v13.json'
        run([sys.executable,root/'story_intelligence_v13.py',video,analysis,edl,'-o',story13,'--target',a.target,'--apply'])
        finish131=work/'finish.v13.1.json'
        run([sys.executable,root/'story_intelligence_v131.py',video,edl,'-o',finish131,'--target',a.target,'--apply'])
        creative14=work/'creative.v14.json'
        run([sys.executable,root/'creative_director_v14.py',edl,'-o',creative14,'--target',a.target,'--apply'])
        # Legacy V14 voice-plan export is not consumed by the V16 narrator.
        # Kept out of the hot path; voice renderer uses voice_plan_v15.
    creative15=work/'creative.v15.json'
    if a.mode!='turbo':run([sys.executable,root/'creative_director_v15.py',edl,'-o',creative15,'--target',a.target,'--apply'])
    # V19: narration must be deliberate and its subtitles must be rendered with the picture.
    from narration_v19 import ensure_narration_plan
    narration_report=ensure_narration_plan(edl, script_path=a.voice_script)
    print('NARRATION V19:', narration_report)
    if narration_report['events']==0 and not a.allow_no_voice:
        raise RuntimeError('No narration script generated. Provide --voice-script SCRIPT.txt or explicitly --allow-no-voice.')
    cmd=[sys.executable,root/'render.py',edl,'-o',first]
    if a.preview: cmd.append('--preview')
    if a.no_subtitles: cmd.append('--no-subtitles')
    else: cmd += ['--build-subtitles','--caption-style',a.caption_style]
    run(cmd)
    ed=json.loads(edl.read_text()); rep=evaluate(first,ed); qc1.write_text(json.dumps(rep,ensure_ascii=False,indent=2)); print(f'QC first pass: {rep["score"]}/100')
    final_src=first
    # Fast mode only pays for a second render when QC is genuinely poor (<76/error).
    repair_threshold=70 if a.mode=='turbo' else (74 if a.mode=='fast' else (80 if a.mode=='smart' else 84))
    needs_repair=(rep['score']<repair_threshold or any(x.get('severity')=='error' for x in rep.get('issues',[])))
    chosen_edl=edl
    if needs_repair and not a.no_auto_repair:
        repaired=work/'edl.repaired.json'; repaired.write_text(json.dumps(repair(ed,rep),ensure_ascii=False,indent=2)); second=work/'second_pass.mp4'; cmd=[sys.executable,root/'render.py',repaired,'-o',second]
        if a.preview: cmd.append('--preview')
        if a.no_subtitles: cmd.append('--no-subtitles')
        else: cmd += ['--build-subtitles','--caption-style',a.caption_style]
        run(cmd); rep2=evaluate(second,json.loads(repaired.read_text())); (work/'qc.second.json').write_text(json.dumps(rep2,ensure_ascii=False,indent=2)); final_src=second if rep2['score']>=rep['score'] else first
        if final_src==second: chosen_edl=repaired
    # Publish only fully verified files. Never depend on third-party upload services.
    output.parent.mkdir(parents=True,exist_ok=True)
    verify_mp4(final_src)
    narrated=work/'narrated_verified.mp4'
    from voice_renderer_v16 import mix
    voice_result={'status':'disabled','lines':0}
    if narration_report['events']:
        try:
            voice_result=mix(final_src,chosen_edl,narrated,work/'voice_v16')
            if voice_result.get('status')!='mixed' or not voice_result.get('lines'):
                raise RuntimeError('Voice renderer returned zero synthesized lines')
            verify_mp4(narrated)
            info=publish_mp4(narrated,output)
        except Exception as e:
            if not a.allow_no_voice:
                raise RuntimeError('AI voice failed: video NOT published. Check Internet, edge-tts and voice plan.') from e
            print('WARNING: narration failed and --allow-no-voice was set:',e)
            info=publish_mp4(final_src,output)
            voice_result={'status':'explicit_fallback_no_tts','lines':0,'error':str(e)}
    else:
        info=publish_mp4(final_src,output)
    voice_status=voice_result['status']
    verification_path=work/'export.verified.json'
    verification_path.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'EXPORT VERIFIED: {output} | {info["duration_seconds"]}s | {info["width"]}x{info["height"]}')
    manifest={'version':'18.0','analysis_cache_hit':cache_hit,'mode':a.mode,'input':str(original),'effective_source':str(video),'output':str(output),'workdir':str(work),'target_seconds':a.target,'aspect':a.aspect,'selected_pass':final_src.name,'selected_edl':str(chosen_edl),'elapsed_seconds':round(time.time()-started,2),'watermark':wm_report,'viral_plan':str(viral12),'story_plan_v13':str(story13) if story13 else None,'finish_plan_v131':str(finish131) if finish131 else None,'creative_plan_v14':str(creative14) if creative14 else None,'voice_plan_v14':None,'creative_plan_v15':str(creative15),'voice_v16_status':voice_status,'voice_v19_lines':voice_result.get('lines',0),'export_validation':str(verification_path),'upload':'not_attempted_local_only'}
    (work/'v17.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)); print(f'\ndone V17 {a.mode} → {output} | {manifest["elapsed_seconds"]}s')
if __name__=='__main__': main()
