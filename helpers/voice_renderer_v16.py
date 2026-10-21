"""V16 safe narration mixer: correct timeline, silent sources, duration caps and atomic output."""
from __future__ import annotations
import argparse, asyncio, json, math, os, shutil, subprocess
from pathlib import Path


def run(cmd):
    subprocess.run([str(x) for x in cmd], check=True, stdout=subprocess.DEVNULL)


def probe(path):
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type','-of','json',str(path)],capture_output=True,text=True,check=True)
    d=json.loads(p.stdout)
    return float(d.get('format',{}).get('duration',0)), any(s.get('codec_type')=='audio' for s in d.get('streams',[]))


def valid_events(events,duration):
    clean=[]
    for e in events:
        try:
            start=float(e['at']); limit=float(e.get('max_seconds',1.8)); content=str(e['text']).strip()
        except (ValueError,KeyError,TypeError): continue
        if not (math.isfinite(start) and math.isfinite(limit)) or start<0 or start>=duration or limit<=0 or not content: continue
        clean.append({'at':start,'max_seconds':min(limit,duration-start),'text':content[:400]})
    clean.sort(key=lambda x:x['at'])
    for i in range(len(clean)-1): clean[i]['max_seconds']=min(clean[i]['max_seconds'],max(0,clean[i+1]['at']-clean[i]['at']-.06))
    return [e for e in clean if e['max_seconds']>=.2]


async def synth(text,out,voice,rate,volume):
    try: import edge_tts
    except ImportError as exc: raise RuntimeError('Missing edge-tts; run SETUP_ONCE.bat') from exc
    await edge_tts.Communicate(text,voice=voice,rate=rate,volume=volume).save(str(out))


def mix(video,edl,output,workdir=None):
    video=Path(video).resolve(); output=Path(output).resolve()
    if video==output: raise ValueError('Output must differ from input')
    ed=json.loads(Path(edl).read_text(encoding='utf-8'))
    plan=ed.get('voice_plan_v15') or {}; duration,has_audio=probe(video)
    events=valid_events(plan.get('events') or [],duration)
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_name(output.stem+'.v16partial'+output.suffix)
    if temp.exists(): temp.unlink()
    if not events:
        shutil.copy2(video,temp); os.replace(temp,output)
        return {'status':'no_voice_events','lines':0,'has_source_audio':has_audio}
    wd=Path(workdir or output.parent/'voice_v16'); wd.mkdir(parents=True,exist_ok=True)
    try:
        voice=plan.get('voice','vi-VN-HoaiMyNeural')
        for i,e in enumerate(events):
            mp3=wd/f'voice_{i:02d}.mp3'
            asyncio.run(synth(e['text'],mp3,voice,plan.get('rate','+4%'),plan.get('volume','+0%')))
            clip=wd/f'voice_{i:02d}.wav'
            # Trim spoken audio to allocated window, never overlap the next line / past end.
            run(['ffmpeg','-y','-loglevel','error','-i',mp3,'-af',f'atrim=duration={e["max_seconds"]:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={max(0,e["max_seconds"]-.12):.3f}:d=0.12','-ar','48000','-ac','2',clip])
            e['clip']=clip
        cmd=['ffmpeg','-y','-loglevel','error','-i',video]
        if not has_audio: cmd+=['-f','lavfi','-t',f'{duration:.3f}','-i','anullsrc=channel_layout=stereo:sample_rate=48000']
        for e in events: cmd+=['-i',e['clip']]
        base=0 if has_audio else 1
        # Duck source only while actual voice windows play.
        gain=10**(max(-30,min(0,float(plan.get('duck_music_db',-10))))/20)
        cond='+'.join(f'between(t,{e["at"]:.3f},{e["at"]+e["max_seconds"]:.3f})' for e in events)
        flt=[f'[{base}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=\'if({cond},{gain:.6f},1)\':eval=frame[base]']
        labels=['[base]']; idx=1 if has_audio else 2
        for i,e in enumerate(events):
            delay=round(e['at']*1000)
            flt.append(f'[{idx+i}:a]adelay={delay}:all=1,volume=1.08[v{i}]')
            labels.append(f'[v{i}]')
        flt.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=first:dropout_transition=0,alimiter=limit=0.95[aout]')
        run([*cmd,'-filter_complex',';'.join(flt),'-map','0:v:0','-map','[aout]','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',temp])
        probe(temp)
        os.replace(temp,output)
        return {'status':'mixed','lines':len(events),'has_source_audio':has_audio}
    finally:
        if temp.exists(): temp.unlink()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('video',type=Path); ap.add_argument('edl',type=Path); ap.add_argument('-o','--output',type=Path,required=True); ap.add_argument('--workdir',type=Path)
    a=ap.parse_args()
    print(json.dumps(mix(a.video,a.edl,a.output,a.workdir),ensure_ascii=False))
if __name__=='__main__':main()
