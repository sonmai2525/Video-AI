# V12 VIRAL ENGINE

V12 changes the goal from "more effects" to "better retention".

Pipeline: Understand -> candidate edits -> Hook -> retention pacing -> sparse pattern interrupts -> render winner -> Quality Gate.

## Modes
- FAST: V5/V6 + V12 candidate scoring. Fastest.
- SMART (default): semantic V8 + story/reframe V9 + V12. Best speed/quality balance.
- MAX: adds V10 multimodal storyboard analysis before V12. Slowest.

## V12 candidate generator
The system builds three edit candidates in memory (emotion, retention, compact), scores hook strength, moment quality, visual variety, pacing and continuity, then renders only the winner. This avoids rendering three full videos.

## Retention rules
- strongest useful moment may become the cold open;
- effects are sparse and intentional;
- pattern interrupts are capped instead of stacked;
- Quality Gate triggers a second render only when needed;
- watermark cleanup remains conservative: edge crop only when safe; no destructive blur/inpainting.

No edit can guarantee views. V12 optimizes editable retention signals, not platform distribution.
