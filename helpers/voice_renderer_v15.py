"""Render Vietnamese neural TTS with edge-tts and mix it into the finished MP4 with music ducking."""
from __future__ import annotations
import argparse,asyncio,json,shutil,subprocess
from pathlib import Path

async def synth(text,out,voice,rate,volume):
    try:
        import edge_tts
    except ImportError as e:
        raise RuntimeError('edge-tts is not installed. Run SETUP_ONCE.bat again.') from e
    c=edge_tts.Communicate(text,voice=voice,rate=rate,volume=volume)
    await c.save(str(out))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('video',type=Path); ap.add_argument('edl',type=Path); ap.add_argument('-o','--output',type=Path,required=True); ap.add_argument('--workdir',type=Path); a=ap.parse_args()
    ed=json.loads(a.edl.read_text(encoding='utf-8')); plan=ed.get('voice_plan_v15') or {}; ev=plan.get('events') or []
    if not ev:
        shutil.copy2(a.video,a.output); print('V15 TTS: no voice events'); return
    wd=a.workdir or a.output.parent/'v15_voice'; wd.mkdir(parents=True,exist_ok=True)
    voice=plan.get('voice','vi-VN-HoaiMyNeural'); rate=plan.get('rate','+4%'); volume=plan.get('volume','+0%')
    clips=[]
    for i,e in enumerate(ev):
        p=wd/f'voice_{i:02d}.mp3'; asyncio.run(synth(e['text'],p,voice,rate,volume)); clips.append(p)
    # Base audio ducks only during spoken windows. Voices are delayed to their timeline positions and mixed.
    inputs=['-i',str(a.video)]
    for p in clips: inputs += ['-i',str(p)]
    windows=[]
    for e in ev:
        st=float(e['at']); en=st+float(e.get('max_seconds',1.8)); windows.append(f'between(t,{st:.3f},{en:.3f})')
    enable='+'.join(windows) or '0'; duck_db=float(plan.get('duck_music_db',-10)); gain=10**(duck_db/20)
    fc=[f"[0:a]volume='if({enable},{gain:.6f},1)'[base]"]
    labels=['[base]']
    for i,e in enumerate(ev,1):
        delay=max(0,int(float(e['at'])*1000)); fc.append(f'[{i}:a]adelay={delay}|{delay},volume=1.15[v{i}]'); labels.append(f'[v{i}]')
    fc.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=first:dropout_transition=0,alimiter=limit=0.95[aout]')
    cmd=['ffmpeg','-y',*inputs,'-filter_complex',';'.join(fc),'-map','0:v:0','-map','[aout]','-c:v','copy','-c:a','aac','-b:a','256k','-ar','48000','-movflags','+faststart',str(a.output)]
    subprocess.run(cmd,check=True); print(f'V15 TTS mixed: {len(ev)} lines, voice={voice}')
if __name__=='__main__':main()
