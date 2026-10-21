from __future__ import annotations
import argparse, configparser, subprocess, sys
from pathlib import Path
VIDEO_EXTS={'.mp4','.mov','.mkv','.avi','.webm','.m4v','.mts','.m2ts'}
ROOT=Path(__file__).resolve().parent.parent

def load_cfg(path):
    c=configparser.ConfigParser(); c.read(path,encoding='utf-8'); s=c['EDIT'] if 'EDIT' in c else {}
    get=lambda k,d:s.get(k,d) if hasattr(s,'get') else d
    return {'mode':get('mode','smart').strip(),'aspect':get('aspect','9:16').strip(),'target':get('target_seconds','20').strip(),'caption':get('caption_style','visual_dynamic').strip(),'watermark':get('watermark_box','').strip(),'preview':get('preview','false').lower() in ('1','true','yes','on'),'auto_repair':get('auto_repair','true').lower() in ('1','true','yes','on')}

def unique_output(outdir,src):
    p=outdir/f'{src.stem}_EDIT.mp4'; n=2
    while p.exists(): p=outdir/f'{src.stem}_EDIT_{n}.mp4'; n+=1
    return p

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('videos',nargs='*'); ap.add_argument('--mode',choices=['turbo','fast','smart','max']); a=ap.parse_args()
    cfg=load_cfg(ROOT/'V16_CONFIG.ini'); mode=a.mode or cfg['mode']; inputs=[Path(x).expanduser().resolve() for x in a.videos]
    if not inputs:
        (ROOT/'INPUT').mkdir(parents=True,exist_ok=True)
        inputs=sorted(p.resolve() for p in (ROOT/'INPUT').iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS)
    inputs=[p for p in inputs if p.exists() and p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    if not inputs:
        print('\nKhong tim thay video. Keo-tha video vao EDIT_VIDEO.bat hoac cho video vao thu muc INPUT.'); return 2
    outdir=ROOT/'OUTPUT'; outdir.mkdir(exist_ok=True); ok=0
    for i,src in enumerate(inputs,1):
        out=unique_output(outdir,src); print(f'\n[{i}/{len(inputs)}] EDIT: {src.name}\nOUTPUT: {out.name}\nMODE: {mode}')
        cmd=[sys.executable,str(ROOT/'helpers'/'auto_viral_editor.py'),str(src),'-o',str(out),'--mode',mode,'--aspect',cfg['aspect'],'--target',cfg['target'],'--caption-style',cfg['caption']]
        script=ROOT/'VOICE_SCRIPT.txt'
        if script.exists() and script.read_text(encoding='utf-8-sig').strip(): cmd += ['--voice-script',str(script)]
        if cfg['watermark']: cmd += ['--watermark-box',cfg['watermark']]
        if cfg['preview']: cmd.append('--preview')
        if not cfg['auto_repair']: cmd.append('--no-auto-repair')
        try: subprocess.run(cmd,cwd=ROOT,check=True); ok+=1
        except subprocess.CalledProcessError as e: print(f'LOI khi edit {src.name}: {e}')
    print(f'\nHOAN TAT: {ok}/{len(inputs)} video. Ket qua: {outdir}')
    return 0 if ok==len(inputs) else 1
if __name__=='__main__': raise SystemExit(main())
