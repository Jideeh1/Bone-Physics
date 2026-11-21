---
name: motion-graphics
description: Design and render professional 2D, 3D and hybrid motion graphics edits (kinetic typography, logo reveals, MoGraph/cloner loops, isometric data stories, beat-synced social "hype"/velocity edits, transitions, title cards) as finished MP4s with synthesized, beat-locked sound. Use when the user asks for a motion graphics piece, animated video, kinetic type, logo animation, looping 3D animation, animated infographic, social reel/TikTok/Short edit, intro/outro, or wants to apply motion design principles (easing, springs, overshoot, stagger, follow-through, motion blur) to code-driven video.
---

# Motion Graphics

Code-driven motion design. Every scene is a **pure function of time** rendered frame-exact in
headless Chromium (Canvas 2D + three.js/WebGL), with real sub-frame **motion blur**, a
**finishing pass** (bloom → chromatic aberration → vignette → grain), and a **synthesized
music bed + SFX** placed on the same timeline. Output: H.264 MP4 + AAC.

```
.claude/skills/motion-graphics/
  render.js          # node render.js scene.js out.mp4 [--still s out.png] [--sheet] [--every n] [--from s --to s]
  audio.py           # numpy synth: drums/bass/pad on a BPM grid + whoosh/impact/riser/pop/click/shimmer/sub/glitch
  lib/mg.js          # easing, springs, keyframes, stagger, beats, noise, shake, trim paths, morphs, glyph layout
  lib/fx.js          # per-shot post: smear (whip), rgbSplit, glitch, zoomBlur, buffer()
  lib/finish.js      # global finishing pass (runs automatically)
  lib/harness.html   # page that hosts scenes, accumulates motion-blur samples
  lib/three.module.min.js   # three.js r169 (vendored, offline)
  templates/scene-2d.js, templates/scene-3d.js
  references/techniques.md  # deep catalogue of techniques, numbers and sources — read for anything non-trivial
```

Requirements: `node` + `playwright` (Chromium), `ffmpeg`, `python3` + `numpy`. Fonts come from the
system (`fc-list`); prefer a variable/heavy family like "Inter Display" for kinetic type.

## Workflow (do these in order — it is how studios work)

1. **Brief → one-line concept.** What is the *single* message, for which platform (aspect ratio,
   length, sound-on/off)? Write the concept as a verb: "the logo *assembles from a bone chain*".
2. **Beat sheet.** Pick a BPM (90 calm · 100–110 corporate · 120–128 energetic · 140+ hype).
   `beat = 60/BPM`. Put every cut, slam and transition on the grid (bar = 4 beats). Write the
   shot list as `t → what happens` before writing code.
3. **Styleframes.** Write the scene, then render 3–6 key stills with `--still` and *look at them*
   (Read the PNGs, hstack with ffmpeg). Fix composition, hierarchy, color and type *here* —
   it's 100× cheaper than in motion.
4. **Animatic.** `--every 3` renders a quick draft to check timing; or `--sheet` for a 12-frame
   contact sheet.
5. **Final render** with full motion blur + audio. Then **QA** (checklist below) on the sheet and
   a few stills taken at transitions.

## Scene API

```js
import * as mg from '/lib/mg.js';      // absolute /lib/ paths — the renderer serves them
import * as fx from '/lib/fx.js';
export default {
  title: 'Name', width: 1080, height: 1920, fps: 30, duration: 8,
  mode: '2d' | '3d' | 'hybrid',          // 3d/hybrid → env.THREE + env.renderer (WebGL, ACES, sRGB)
  motionBlur: { samples: 8, shutter: 180 },   // sub-frame accumulation, centered shutter
  finish: { grain: .06, vignette: .35, ca: 4, bloom: { strength: .5, radius: 30, threshold: .65 }, vignetteCenter: [.5,.5] },
  audio: { bpm: 120, start: 0, kick: 'x...x...x...x...', clap: '....x.......x...', hat: '..x...x...x...x.',
           bass: 'x..x..x.x..x..x.', bassNotes: ['A1','A1','F1','G1'], pad: [['A3','C4','E4']],
           musicTo: 7.6, events: [{ t: 2, type: 'whoosh', dur: .4 }, { t: 4, type: 'impact' }] },
  async setup(env) { /* build meshes/buffers once */ },
  render(t, env) { /* draw the frame for time t (seconds) into env.ctx (2D) and/or env.renderer */ },
};
```
- `render` is called several times per frame (motion-blur subsamples) at arbitrary `t` —
  **never keep state between calls**; derive everything from `t`.
- In 2d mode draw your own background every frame. In 3d/hybrid the WebGL canvas is composited
  *under* `env.ctx`; for transitions that must affect 3D too, `drawImage(env.renderer.domElement)`
  into an `fx.buffer()` and post it (see `examples/05_hype_edit.js`).
- `env.frameTime` = the frame's center time. Use it for anything that must stay **crisp** under
  motion blur: counters, changing digits, UI text, subtitles.
- Audio `events`: `whoosh` is **centered** on `t`; `riser` **ends** on `t` (lands on the hit);
  everything else **starts** at `t`. Music ducks under the kick automatically (sidechain pump).

## The craft — rules that separate pro from amateur

**Easing (the #1 quality signal).**
- Nothing that starts/stops moves linearly. Linear is only for constant motion: spins, loops,
  scrolling tickers, travel *through* a cut.
- Default mograph curve is asymmetric: heavy ease-out (`'snap'`, `'outExpo'`, `'decel'`). Entrances
  decelerate (`decel` = M3 emphasized 0.05,0.7,0.1,1); exits accelerate (`accel` 0.3,0,0.8,0.15).
- Think in the **speed graph**: a good move is one sharp peak early, long tail into the key.
  Sharp corners in the value curve = jerks. If the speed graph is flat, it's linear — fix it.
- Overshoot with **physics**, not hand-keyed bounces: `mg.spring(t-start, {freq, damping})`.
  damping 0.3–0.45 = playful; 0.6–0.8 = corporate; ≥1 = no overshoot.
- **Numbers never overshoot** (a counter reading 103% then 100% looks like a bug): use `outExpo`.

**Timing (30 fps).** micro feedback 4–8 f · UI/secondary 8–15 f · standard move 12–20 f ·
hero move 20–40 f · hold a read-critical title ≥ 1 s per ~3 words (rule of thumb) · hold the
end card ≥ 1.5 s. Cut and slam **on** the beat; anticipation/whoosh starts *before* it.
Durations scale with distance and size: big things move slower.

**Stagger & offset.** 1–3 frames per glyph, 2–5 per list item (`mg.stagger(i,n,each,from)`).
`'center'` and `'end'` directions read as intentional; `'random'` for organic. Offsetting
identical animations is the cheapest way to make motion feel designed.

**The 12 principles, mograph edition.** squash & stretch (`mg.squash(speed)`, preserve volume) ·
anticipation (small opposite move 4–8 f before) · staging (one focal point per moment) ·
straight-ahead vs pose-to-pose (procedural vs keyed `mg.track`) · follow-through & overlapping
action (children lag parents: per-element spring with delay, `mg.inertial`) · slow in/out
(easing) · arcs (move along curves, rotate into travel direction) · secondary action (ticks,
particles, background grid) · timing · exaggeration · solid drawing (consistent light/perspective) · appeal.

**Hierarchy & composition.** One hero per moment; everything else lower contrast/size/motion.
Motion contrast is hierarchy: the fastest, biggest move is what the eye reads. 60/30/10 color
(bg / primary / accent; `mg.palettes`). Respect safe areas: 9:16 keep text inside ~x 90–990,
y 250–1500 (platform UI covers the bottom ~420 px and top ~220 px); 16:9 title-safe ≈ inner 90%.
Sound-off is the default on social → the story must read from type and picture alone.

**Transitions — pick by meaning.** hard cut on beat (default; strongest) · mask/matte wipe (reveal a
new idea) · whip pan with directional smear (energy, same-space jump) · match cut / shape morph
(continuity between two ideas — keep the shape, change the meaning) · zoom-through with radial blur
(go deeper) · glitch/RGB split (digital, disruptive; ≤ 4 frames) · flash frame (1–2 white frames on a
drop) · color-block wipe (graphic, brand). One transition type per piece, plus one "special".

**Kinetic typography.** Words land on beats; one idea per screen; vary weight (200 vs 900) and
scale to create rhythm; reveals: mask-rise from a baseline clip (`maskRise` pattern), per-glyph
stagger, tracking expand/compress (compress = "locking in"), type-on, slam with spring scale,
outline/solid stacks, skew on fast moves. Short words big, long words small.

**3D.** Three-point light (warm key with shadows, cool rim behind, hemisphere fill) · ACES
tone-mapping · fog for aerial perspective · long lenses (FOV 25–40) feel premium · orthographic +
35.264° tilt + 45° yaw = true isometric · chrome needs an environment: build a studio scene of
emissive panels and PMREM it (`examples/05`) · MoGraph = **cloner** (InstancedMesh) + **stacked
effectors** (fields: radial, noise, step/selection) feeding scale/rotation/color.

**Seamless loops.** Every term must be periodic in the loop length: use `phase = t/D·2π`,
`mg.loopNoise`, `%`. Camera orbits only loop if the scene is symmetric under that rotation — and
then the *lights and every field* must rotate with the camera too (see `examples/03_mograph_cloner.js`). Verify:
render `--still 0` and `--still D` with grain off and compare (`ffmpeg -lavfi psnr`; > 40 dB = seamless).

**Finishing.** Order: (CA) → bloom → vignette → **grain last**. Subtle wins: grain .03–.09,
vignette .15–.5, CA 2–6 px, bloom threshold .6–.75. Off-center vignette steers the eye.

**Motion blur.** 180° shutter is the film standard; 200–270° for smeary stylized hits. Fast
scale slams need 10–12 samples or you'll see stepped copies; slow 3D needs 3–5. Never let numbers
blur (use `env.frameTime`).

**Sound.** Beat-based sync for repeating moves, cue-based for hits. Whoosh centered on a
transition, riser ending on the impact, hit on the *contact frame*, flash frame + impact + shake
together on the drop. 3–6 accent SFX per 10 s — restraint. Fade music before the end card ends.

## Recipes (each is a working example in `examples/`; rendered MP4s live in `motion-graphics/edits/` of the bone-physics repo)

| Deliverable | File | Core moves |
|---|---|---|
| Kinetic type, 9:16, 120 BPM | `01_kinetic_type.js` | mask-rise stacks, spring slams, tracking build, color wipes, drop shake + flash |
| Logo reveal, 16:9 | `02_logo_reveal.js` | anticipation squash → pop + shockwave, dual trim-path chase, circle→hex morph, lagged bone chain (follow-through), reveal-from-behind matte, light sweep |
| 3D MoGraph loop, 1:1 | `03_mograph_cloner.js` | instanced hex cloner, ripple + noise + selection effectors, color ramp, symmetric 60° orbit loop |
| Isometric data story, 16:9 hybrid | `04_isometric_data.js` | ortho iso camera, staggered spring bars, data transition, projected 2D labels, crisp counters |
| Hype / velocity edit, 9:16 hybrid | `05_hype_edit.js` | chrome PMREM hero, whip + smear, particle burst, glitch, speed-ramped tunnel, zoom-through, punch + shake |

Start new pieces from `templates/scene-2d.js` or `templates/scene-3d.js`.

## mg.js cheat sheet

`seg(t,start,dur,ease)` eased 0→1 · `prog` linear · `track([{t,v,e}])` keyframes (numbers/arrays) ·
`spring(t,{freq,damping})` · `inertial(tSinceStop,vel,amp,freq,decay)` · `squash(speed)` ·
`vel(f,t)` · `stagger(i,n,each,from)` · `beat(bpm,n)` · `beatPulse(t,bpm,decay,offset)` ·
`noise1/2/3`, `fbm`, `wiggle(t,freq,amp,seed)`, `loopNoise(t,period)` · `shake(t,start,{amp,freq,decay,rot})` ·
`trimPath(ctx,d,start,end,offset)` · `samplePath(d,n)` · `circlePts/polygonPts/alignPts/morphPts` ·
`glyphs(ctx,str,tracking)` per-letter layout · `rrect/poly/xform/project` · `palettes`, `rgba`, `mixColor`.
Eases: Penner set (`in/out/inOut` × Quad…Expo, Circ, Back, Elastic, Bounce) + `easyEase` (AE F9),
`smooth`, `snap`, `whip`, `decel`, `accel`, `standard`, or any `bezier(x1,y1,x2,y2)`.
fx.js: `buffer(name,w,h)`, `smear(ctx,src,dx,dy)`, `rgbSplit(ctx,src,off,angle)`, `glitch(ctx,src,amount,seed)`, `zoomBlur(ctx,src,cx,cy,amount)`.

## QA checklist (run before delivering)

- [ ] Rendered stills at every transition + the end card and actually looked at them.
- [ ] No text outside safe areas or clipped at frame edges; nothing unintentionally overlapping.
- [ ] Every move eased; no linear starts/stops; overshoots only where intended; numbers don't overshoot.
- [ ] Cuts/slams land on beat frames; SFX on contact frames; audio fades before video ends.
- [ ] Motion blur looks continuous (no stepped copies) — raise `samples` on fast shots.
- [ ] Loops verified with PSNR; end card held ≥ 1.5 s; first 1–2 s hooks (social).
- [ ] Contrast/legibility on mobile size (view the contact sheet at thumbnail scale).
- [ ] File plays: `ffprobe out.mp4` shows h264 yuv420p + aac, correct duration and fps.

## Gotchas learned the hard way

- ES-module scenes must be served over HTTP (render.js does this); import libs as `/lib/...`.
- `globalCompositeOperation='multiply'` over transparent pixels writes the fill color — fill opaque black first.
- `source-atop` on an opaque layer paints the background too; for a light sweep, redraw the glyphs with a gradient fill.
- `ctx.clip()` for mask reveals: save/restore around it or every later draw is clipped.
- WebGL readback needs `preserveDrawingBuffer: true` (the harness sets it).
- Software WebGL is slow (~0.3–1.5 s per sample at 1080p): keep 3D motion-blur samples at 3–5 and draft with `--every 3`.
