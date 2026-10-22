"""ChatGPT-friendly, fail-closed narration+animated captions export.
Runs with ffmpeg/ffprobe and Python stdlib; edge-tts is optional. It never uploads files.
Input should be an already-edited video; it does not infer scripts from frames.
"""
from __future__ import annotations
import argparse, asyncio, json, math, re, shutil, subprocess, tempfile
from pathlib import Path


def command(cmd):
    p=subprocess.run([str(x) for x in cmd],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(f"Command failed ({p.returncode}): {p.stderr[-1600:]}")
    return p.stdout


def media_info(path):
    d=json.loads(command(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,codec_name,width,height','-of','json',path]))
    streams=d.get('streams',[])
    video=next((s for s in streams if s.get('codec_type')=='video'),None)
    if not video: raise ValueError('Video stream missing')
    return {'duration':float(d['format']['duration']),'width':video['width'],'height':video['height'],'has_audio':any(s['codec_type']=='audio' for s in streams)}


def parse_boxes(raw,w,h):
    boxes=[]
    if not raw: return boxes
    for box in raw.split(';'):
        v=[int(x) for x in box.split(',')]
        if len(v)!=4: raise ValueError('Logo box must be x,y,w,h;...')
        x,y,bw,bh=v
        if x<0 or y<0 or bw<2 or bh<2 or x+bw>w or y+bh>h or bw*bh>w*h*.12:
            raise ValueError(f'Logo box invalid or overly large: {v}')
        boxes.append(v)
    return boxes


def ass_time(t):
    cs=max(0,int(round(t*100))); return f'{cs//360000}:{(cs//6000)%60:02d}:{(cs//100)%60:02d}.{cs%100:02d}'


def escape(t):
    return t.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n',' ')


def captions(script,duration,w,h,location='bottom'):
    lines=[l.strip() for l in script.splitlines() if l.strip()]
    if not lines: raise ValueError('Script is empty; refusing silent narration export')
    weights=[max(1,len(l.split())) for l in lines]
    total=sum(weights); times=[]; cursor=0
    for i,(line,weight) in enumerate(zip(lines,weights)):
        end=duration if i==len(lines)-1 else cursor+duration*weight/total
        times.append((cursor,end,line)); cursor=end
    # ASS PlayRes matches original dimensions; MarginV is in original pixels.
    margin=int(h*(.19 if location=='bottom' else .32))
    fs=max(22,int(w*.052)); outline=max(2,int(fs*.095))
    header=f'''[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Voice,DejaVu Sans,{fs},&H00FFFFFF,&H0000DEFF,&H00202020,&H68000000,-1,0,0,0,100,100,0,0,1,{outline},1,2,28,28,{margin},1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
    events=[]
    for start,end,line in times:
        words=line.split()
        # Timing approximate and distributed across written words; not forced alignment.
        chunk_count=max(1,math.ceil(len(words)/4))
        for j in range(chunk_count):
            part=words[j*4:(j+1)*4]
            a=start+(end-start)*j/chunk_count; b=start+(end-start)*(j+1)/chunk_count
            centis=max(1,int(round((b-a)*100/max(1,len(part)))))
            body='{\\fad(90,100)\\fscx108\\fscy108\\t(0,140,\\fscx100\\fscy100)}'+''.join(f'{{\\k{centis}}}'+escape(word)+' ' for word in part)
            events.append(f'Dialogue: 0,{ass_time(a)},{ass_time(b)},Voice,,0,0,0,,{body}\n')
    return header+''.join(events)


async def edge_generate(script, path,voice):
    import edge_tts
    await edge_tts.Communicate(' '.join(x.strip() for x in script.splitlines() if x.strip()), voice=voice).save(str(path))


def render(video,output,script_path,audio_path=None,voice='vi-VN-HoaiMyNeural',boxes='',caption_position='bottom'):
    video=Path(video).resolve(); output=Path(output).resolve(); script_path=Path(script_path).resolve()
    if output==video: raise ValueError('Output cannot overwrite source')
    if not video.exists() or not script_path.exists(): raise FileNotFoundError('Input video or script missing')
    script=script_path.read_text(encoding='utf-8-sig').strip()
    meta=media_info(video); regions=parse_boxes(boxes,meta['width'],meta['height'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v21_',dir=output.parent) as t:
        tmp=Path(t); speech=Path(audio_path).resolve() if audio_path else tmp/'voice.mp3'
        if audio_path:
            if not speech.exists(): raise FileNotFoundError('Narration audio not found')
        else:
            try: asyncio.run(edge_generate(script,speech,voice))
            except Exception as exc: raise RuntimeError('AI voice generation unavailable. Supply --voice-file with your own MP3/WAV; no silent video was exported.') from exc
        if not speech.exists() or speech.stat().st_size<500: raise RuntimeError('Narration audio missing or empty')
        speech_meta=json.loads(command(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type','-of','json',speech]))
        if not any(s['codec_type']=='audio' for s in speech_meta.get('streams',[])): raise RuntimeError('Narration file does not contain audio')
        spoken=float(speech_meta['format']['duration'])
        if spoken>meta['duration']+.15:
            raise RuntimeError(f'Narration {spoken:.1f}s exceeds video {meta["duration"]:.1f}s. Shorten script or provide a longer video.')
        subs=tmp/'voice.ass'; subs.write_text(captions(script, max(.1,spoken),meta['width'],meta['height'],caption_position),encoding='utf-8')
        filters=[f'delogo=x={x}:y={y}:w={w}:h={h}:show=0' for x,y,w,h in regions]
        filters.append('subtitles='+str(subs).replace('\\','/').replace(':','\\:').replace("'", "\\'"))
        vf=','.join(filters)
        cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-i',video,'-i',speech]
        # Mix music/source audio softly, narration prominently. If none, use narration only.
        if meta['has_audio']:
            cmd+=['-filter_complex','[0:a]volume=0.16[bed];[bed][1:a]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.95[a]', '-map','0:v:0','-map','[a]']
        else: cmd+=['-map','0:v:0','-map','1:a:0']
        candidate=tmp/'candidate.mp4'
        cmd+=['-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','192k','-t',str(meta['duration']),'-movflags','+faststart',candidate]
        command(cmd)
        result=media_info(candidate)
        if not result['has_audio'] or result['duration']<meta['duration']*.9: raise RuntimeError('Export validation failed: audio missing or short output')
        # Audio-stream verification cannot certify voice content; the input speech file was checked separately.
        shutil.move(candidate,output)
    return {'status':'exported_with_narration_track','output':str(output),'source_duration':meta['duration'],'narration_duration':spoken,'logo_regions':regions,'caption_timing':'estimated_by_word_count','tts':'supplied_audio' if audio_path else 'edge_tts'}


def main():
    p=argparse.ArgumentParser(description='ChatGPT V21 final voice/captions/logo export; no external uploading')
    p.add_argument('video'); p.add_argument('--script',required=True); p.add_argument('--output',required=True)
    p.add_argument('--voice-file',help='Pre-generated AI narration .mp3/.wav if TTS Internet blocked')
    p.add_argument('--voice',default='vi-VN-HoaiMyNeural'); p.add_argument('--logo-boxes',default=''); p.add_argument('--caption-position',choices=['bottom','middle'],default='bottom')
    a=p.parse_args()
    print(json.dumps(render(a.video,a.output,a.script,a.voice_file,a.voice,a.logo_boxes,a.caption_position),ensure_ascii=False,indent=2))
if __name__=='__main__': main()
