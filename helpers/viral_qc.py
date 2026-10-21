"""V7 output QC + conservative auto-repair for short-form edits.

Checks structural quality without pretending to judge virality: output existence/duration,
black/frozen-frame warnings, audio peak, effect density, tiny cuts, speed bounds and
low-confidence text placement. Can write a repaired EDL for one re-render pass.
"""
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path


def _run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def probe(path: Path):
    p=_run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)])
    if p.returncode: return {'ok':False,'error':p.stderr.strip()}
    d=json.loads(p.stdout); fmt=d.get('format',{}); streams=d.get('streams',[])
    v=next((x for x in streams if x.get('codec_type')=='video'),{}); a=next((x for x in streams if x.get('codec_type')=='audio'),None)
    return {'ok':True,'duration':float(fmt.get('duration') or v.get('duration') or 0),'width':v.get('width'),'height':v.get('height'),'has_audio':bool(a),'size':int(fmt.get('size') or 0)}

def detect_video_warnings(path: Path):
    p=_run(['ffmpeg','-hide_banner','-i',str(path),'-vf','blackdetect=d=0.35:pix_th=0.10,freezedetect=n=-50dB:d=1.5','-an','-f','null','-'])
    black=[]; freeze=[]
    for m in re.finditer(r'black_start:([0-9.]+).*?black_end:([0-9.]+)',p.stderr): black.append([round(float(m.group(1)),3),round(float(m.group(2)),3)])
    for m in re.finditer(r'freeze_start:([0-9.]+)',p.stderr): freeze.append(round(float(m.group(1)),3))
    return black,freeze

def audio_peak(path: Path):
    p=_run(['ffmpeg','-hide_banner','-i',str(path),'-af','volumedetect','-vn','-f','null','-'])
    m=re.search(r'max_volume:\s*(-?[0-9.]+) dB',p.stderr)
    return float(m.group(1)) if m else None

def evaluate(video: Path, edl: dict):
    meta=probe(video); issues=[]; score=100
    if not meta.get('ok'): return {'pass':False,'score':0,'issues':[{'severity':'error','code':'probe_failed','detail':meta.get('error')}], 'meta':meta}
    target=float((edl.get('short_form') or {}).get('target_seconds') or meta['duration'])
    if meta['duration'] < max(.5,target*.55): issues.append({'severity':'error','code':'too_short','detail':f'{meta["duration"]:.2f}s vs target {target:.2f}s'}); score-=30
    if meta['duration'] > target*1.35+1: issues.append({'severity':'warn','code':'too_long','detail':f'{meta["duration"]:.2f}s vs target {target:.2f}s'}); score-=12
    ranges=edl.get('ranges') or []
    tiny=[i for i,r in enumerate(ranges) if (float(r['end'])-float(r['start']))/max(.01,float(r.get('speed',1))) < .22]
    if tiny: issues.append({'severity':'warn','code':'tiny_cuts','detail':tiny}); score-=min(15,3*len(tiny))
    extreme=[i for i,r in enumerate(ranges) if not .82 <= float(r.get('speed',1)) <= 1.25]
    if extreme: issues.append({'severity':'warn','code':'extreme_speed','detail':extreme}); score-=min(12,3*len(extreme))
    motions=sum(1 for r in ranges if r.get('motion') not in (None,'none'))
    if ranges and motions/len(ranges)>.72: issues.append({'severity':'warn','code':'effect_density','detail':round(motions/len(ranges),2)}); score-=8
    low=[i for i,e in enumerate(edl.get('visual_text_events') or []) if float(e.get('confidence',1))<.45]
    if low: issues.append({'severity':'warn','code':'low_text_confidence','detail':low}); score-=min(10,2*len(low))
    black,freeze=detect_video_warnings(video)
    if black: issues.append({'severity':'warn','code':'black_frames','detail':black[:6]}); score-=min(15,5*len(black))
    if freeze: issues.append({'severity':'warn','code':'long_freeze','detail':freeze[:6]}); score-=min(12,4*len(freeze))
    peak=audio_peak(video) if meta.get('has_audio') else None
    if meta.get('has_audio') and peak is not None and peak < -18: issues.append({'severity':'warn','code':'audio_too_quiet','detail':peak}); score-=10
    return {'pass':score>=82 and not any(x['severity']=='error' for x in issues),'score':max(0,score),'issues':issues,'meta':meta,'audio_peak_db':peak}

def repair(edl: dict, report: dict):
    out=json.loads(json.dumps(edl)); codes={x['code'] for x in report.get('issues',[])}
    ranges=[]
    for r in out.get('ranges') or []:
        rr=dict(r); dur=float(rr['end'])-float(rr['start'])
        if dur/max(.01,float(rr.get('speed',1)))<.22: continue
        rr['speed']=round(min(1.22,max(.85,float(rr.get('speed',1)))),3)
        ranges.append(rr)
    if 'effect_density' in codes:
        for i,r in enumerate(ranges):
            if i%2: r['motion']='none'
    out['ranges']=ranges
    for e in out.get('visual_text_events') or []:
        if float(e.get('confidence',1))<.45:
            e['motion']='rise'; e['style']='clean'; e['layout']='upper'; e['confidence']=.55; e['reason']='v7_qc_safe_fallback'
    out.setdefault('v7_qc',{})['auto_repaired']=True; out['v7_qc']['source_score']=report.get('score')
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('video',type=Path); ap.add_argument('edl',type=Path); ap.add_argument('-o','--output',type=Path); ap.add_argument('--repair-edl',type=Path)
    a=ap.parse_args(); edl=json.loads(a.edl.read_text()); rep=evaluate(a.video,edl)
    out=a.output or a.video.with_suffix('.qc.json'); out.write_text(json.dumps(rep,ensure_ascii=False,indent=2)); print(f'QC score {rep["score"]}/100 | pass={rep["pass"]} | {len(rep["issues"])} issue(s)')
    if a.repair_edl: a.repair_edl.write_text(json.dumps(repair(edl,rep),ensure_ascii=False,indent=2)); print(f'wrote repaired EDL → {a.repair_edl}')
if __name__=='__main__': main()
