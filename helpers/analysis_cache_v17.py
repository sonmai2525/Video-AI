"""Shared per-file analysis cache, invalidated by file stat and analysis settings."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path

VERSION = 'v17-analyze-2'
def key_for(video:Path, quick:bool, threshold:float)->str:
    p=video.resolve(); st=p.stat()
    # Re-hash bounded portions to catch edits with preserved size/mtime.
    hh=hashlib.sha256()
    with p.open('rb') as f:
        hh.update(f.read(65536))
        if st.st_size>65536:
            f.seek(max(0,st.st_size-65536));hh.update(f.read(65536))
    data=[str(p),st.st_size,st.st_mtime_ns,hh.hexdigest(),quick,float(threshold),VERSION]
    return hashlib.sha256(json.dumps(data).encode()).hexdigest()

def analyze_cached(video:Path,output:Path,quick:bool=False,threshold:float=.30,cache_dir:Path|None=None,no_cache:bool=False)->bool:
    output.parent.mkdir(parents=True,exist_ok=True)
    cache_dir=cache_dir or Path.home()/'.video_ai_editor_cache_v17'
    key=key_for(video,quick,threshold)
    path=cache_dir/(key+'.json')
    if not no_cache and path.exists():
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            if data.get('source')==str(video.resolve()) and 'scenes' in data:
                shutil_copy(path,output);return True
        except (OSError,ValueError,TypeError):pass
    cmd=[sys.executable,str(Path(__file__).parent/'analyze_short.py'),str(video),'-o',str(output),'--scene-threshold',str(threshold)]
    if quick:cmd.append('--quick')
    subprocess.run(cmd,check=True)
    if not no_cache:
        cache_dir.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix='.analysis-',suffix='.json',dir=cache_dir)
        try:
            with os.fdopen(fd,'wb') as f:f.write(output.read_bytes())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    return False

def shutil_copy(a,b):
    import shutil
    if a.resolve()!=b.resolve():shutil.copy2(a,b)
