# V7 Auto Viral Editor

V7 wraps the V2–V6 pipeline into one command and adds an objective QC/re-render loop.

```bash
python helpers/auto_viral_editor.py input.mp4 -o final.mp4 --target 20 --aspect 9:16
```

Pipeline: scene/beat analysis → starter EDL → V5 visual text placement → V6 creative edit plan → render → V7 QC → conservative EDL repair → optional second render → keep the higher-scoring pass.

QC checks output duration, tiny cuts, extreme speed, excessive motion density, low-confidence text placement, black/frozen frames and audio peak. Auto-repair removes unusably tiny cuts, clamps speed, reduces excessive camera motion and falls back to safer text styling/placement for low-confidence events.

**Important:** the score is a technical/edit-quality heuristic, not a promise that a video will go viral. Semantic story judgment and trend awareness still benefit from a multimodal/LLM review.
