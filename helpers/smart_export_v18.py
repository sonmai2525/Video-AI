"""V18 local-first MP4 verification and atomic publication. No network uploads."""
from __future__ import annotations
import json, os, subprocess, shutil
from pathlib import Path

class ExportError(RuntimeError): pass

def verify_mp4(path, minimum_bytes=1024):
    path=Path(path)
    if not path.is_file() or path.stat().st_size < minimum_bytes:
        raise ExportError(f"Output absent or too small: {path}")
    cmd=['ffprobe','-v','error','-show_entries','format=duration,format_name:stream=codec_type,codec_name,width,height','-of','json',str(path)]
    try:
        result=subprocess.run(cmd,capture_output=True,text=True,check=True,timeout=35)
        meta=json.loads(result.stdout)
        duration=float(meta.get('format',{}).get('duration',0))
        video=[s for s in meta.get('streams',[]) if s.get('codec_type')=='video']
        if duration<=0 or not video or not all(int(video[0].get(k,0))>0 for k in ('width','height')):
            raise ExportError(f"Invalid video stream or duration: {path}")
        if 'mp4' not in meta.get('format',{}).get('format_name','') and 'mov' not in meta.get('format',{}).get('format_name',''):
            raise ExportError(f"Unexpected format: {path}")
        return {'status':'verified','file':str(path),'duration_seconds':round(duration,3),'width':int(video[0]['width']),'height':int(video[0]['height']),'bytes':path.stat().st_size,'video_codec':video[0].get('codec_name','unknown'),'has_audio':any(s.get('codec_type')=='audio' for s in meta.get('streams',[]))}
    except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired,ValueError,KeyError,TypeError) as e:
        raise ExportError(f"Cannot verify MP4 {path}: {e}") from e

def publish_mp4(source,destination):
    source=Path(source).resolve(); destination=Path(destination).resolve()
    verify_mp4(source)
    destination.parent.mkdir(parents=True,exist_ok=True)
    tmp=destination.with_name(destination.stem+'.export-partial'+destination.suffix)
    if tmp.exists(): tmp.unlink()
    try:
        shutil.copy2(source,tmp)
        info=verify_mp4(tmp)
        os.replace(tmp,destination)
        info['file']=str(destination)
        return info
    finally:
        if tmp.exists(): tmp.unlink()
