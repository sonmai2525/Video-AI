"""Repeatable analysis cache benchmark; requires ffmpeg/ffprobe and numpy."""
from __future__ import annotations
import argparse,time,tempfile
from pathlib import Path
from analysis_cache_v17 import analyze_cached

def main():
    p=argparse.ArgumentParser();p.add_argument('video',type=Path);p.add_argument('--quick',action='store_true');args=p.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        t=Path(temp);measure=[]
        for i in range(2):
            start=time.perf_counter();hit=analyze_cached(args.video.resolve(),t/'analysis.json',quick=args.quick,cache_dir=t/'cache');measure.append(time.perf_counter()-start)
            print(f'run {i+1}: {measure[-1]:.3f}s (cache {"HIT" if hit else "MISS"})')
        print('Measured analysis only; does not include editing/render/voice.')
if __name__=='__main__':main()
