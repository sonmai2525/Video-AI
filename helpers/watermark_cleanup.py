"""V10.1 conservative watermark cleanup.

Design goal: never replace a small logo with a large smeared patch. Edge watermarks are
removed by a small crop (highest quality). Interior marks are left untouched by default
unless the caller explicitly requests inpaint.

Box syntax is pixels: x,y,w,h in source coordinates.
"""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path


def probe(path: Path):
    p=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',str(path)],capture_output=True,text=True,check=True)
    s=json.loads(p.stdout)['streams'][0]; return int(s['width']),int(s['height'])

def parse_box(s:str):
    v=[int(float(x.strip())) for x in s.split(',')]
    if len(v)!=4: raise ValueError('watermark box must be x,y,w,h')
    return v

def edge_crop(width,height,box,max_loss=.12,pad=4):
    x,y,w,h=box; x=max(0,x-pad); y=max(0,y-pad); w=min(width-x,w+2*pad); h=min(height-y,h+2*pad)
    candidates=[]
    if y<=pad*2: candidates.append(('top',h/height,(0,h,width,height-h)))
    if y+h>=height-pad*2: candidates.append(('bottom',h/height,(0,0,width,height-h)))
    if x<=pad*2: candidates.append(('left',w/width,(w,0,width-w,height)))
    if x+w>=width-pad*2: candidates.append(('right',w/width,(0,0,width-w,height)))
    candidates=[c for c in candidates if c[1] <= max_loss and c[2][2]>32 and c[2][3]>32]
    return min(candidates,key=lambda z:z[1]) if candidates else None

def clean(src:Path,dst:Path,box,mode='auto',max_crop=.12):
    W,H=probe(src); choice=edge_crop(W,H,box,max_crop)
    report={'source':str(src),'box':box,'mode_requested':mode,'width':W,'height':H}
    if mode in ('auto','crop') and choice:
        side,loss,(cx,cy,cw,ch)=choice
        # Crop is intentionally NOT scaled back. Later 9:16 reframing consumes the clean frame,
        # avoiding blur from an unnecessary resize cycle.
        vf=f'crop={cw}:{ch}:{cx}:{cy}'
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(src),'-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','17','-c:a','copy',str(dst)],check=True)
        report.update({'applied':True,'method':'edge_crop','side':side,'frame_loss_ratio':round(loss,4),'filter':vf})
    else:
        # Safe refusal: a persistent interior watermark cannot be reconstructed reliably from
        # ordinary neighbouring frames. Do not blur/delogo it automatically.
        dst.write_bytes(src.read_bytes())
        report.update({'applied':False,'method':'preserve_source','reason':'interior_or_large_watermark; destructive blur/inpaint disabled'})
    return report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('video',type=Path); ap.add_argument('-o','--output',type=Path,required=True); ap.add_argument('--box',required=True,help='x,y,w,h pixels'); ap.add_argument('--mode',choices=['auto','crop'],default='auto'); ap.add_argument('--max-crop',type=float,default=.12); ap.add_argument('--report',type=Path)
    a=ap.parse_args(); a.output.parent.mkdir(parents=True,exist_ok=True); rep=clean(a.video,a.output,parse_box(a.box),a.mode,a.max_crop); rp=a.report or a.output.with_suffix('.watermark.json'); rp.write_text(json.dumps(rep,ensure_ascii=False,indent=2)); print(json.dumps(rep,ensure_ascii=False))
if __name__=='__main__': main()
