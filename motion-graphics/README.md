# Motion graphics edits

Five edits made with the `motion-graphics` Claude skill (`.claude/skills/motion-graphics/`).
Each `.js` file is the full source for its `.mp4`. The `.sheet.png` next to it is a 12-frame contact sheet.

| # | Edit | Format | Showcases |
|---|------|--------|-----------|
| 01 | Kinetic Type | 9:16 · 10 s · 120 BPM | mask-rise type, spring slams, tracking build, diagonal color wipes, drop shake + flash frame |
| 02 | Logo Reveal | 16:9 · 8 s | anticipation → pop, trim-path ring chase, circle→hexagon morph, bone chain with follow-through, reveal-from-behind matte, light sweep |
| 03 | Hex Field | 1:1 · 8 s seamless loop · 3D | MoGraph-style cloner with stacked effectors (ripple, noise, selection), color ramp, symmetric orbit loop |
| 04 | Isometric Data Story | 16:9 · 8 s · 3D + 2D | orthographic isometric camera, spring bars, data transition, projected labels, crisp counters |
| 05 | Hype Edit | 9:16 · 8 s · 128 BPM · 3D + 2D | chrome hero, whip pan, particle burst, glitch, speed-ramped tunnel, zoom-through, end card |

Re-render any edit (needs node + playwright, ffmpeg, python3 + numpy):

```bash
node .claude/skills/motion-graphics/render.js motion-graphics/edits/02_logo_reveal.js out.mp4 --sheet
node .claude/skills/motion-graphics/render.js motion-graphics/edits/02_logo_reveal.js frame.png --still 4.5
```

In Claude Code, ask for a motion graphics piece (e.g. "make a 6-second logo reveal for ACME, 9:16") and the skill loads automatically.
