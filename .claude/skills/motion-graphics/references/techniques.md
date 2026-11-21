# Motion Graphics Techniques — research reference

A catalogue of what working motion designers use, distilled from tutorials, studio breakdowns,
platform docs and design-system specs (sources at the end). Each entry: **what** · **when** ·
**how here** (mg.js/fx.js implementation). Numbers marked *(rule of thumb)* are practitioner
heuristics, not standards: test them against your piece.

---

## 1. Foundations

### 1.1 Easing & the graph editor
- **Value graph** = property over time; **speed graph** = its derivative. Two moves can look the
  same in the value graph but feel different; the speed graph shows the difference.
- AE "Easy Ease" = 33% influence ≈ `bezier(.33,0,.67,1)` → `ease.easyEase`. Pros drag influence to
  70–90% for the "snappy" mograph curve → `ease.snap` (`.8,0,.1,1`), `ease.whip` (`.9,0,.1,1`).
- Stopping move: speed approaches 0 at the final key, and the value curve shouldn't overshoot unless you mean it to.
- Material 3 tokens: emphasized-decelerate `(.05,.7,.1,1)` for entering, emphasized-accelerate
  `(.3,0,.8,.15)` for exiting, standard `(.2,0,0,1)` for utility moves; ~300 ms for quick motion and ~500–650 ms for
  emphasized/long motion. Long + emphasized reads as stylized.
- Corporate pieces: gentle curves, little overshoot. Cartoony/social: big overshoot, elastic.

### 1.2 Disney's 12 principles applied to motion design
From Johnston & Thomas, *The Illusion of Life* (1981), adapted by motion designers:
- **Squash & stretch:** stretch along velocity, squash on impact, preserve area: `mg.squash(speed)`.
- **Anticipation:** a small move opposite the action before it (dot squashes before popping, `examples/02`).
- **Staging:** one readable silhouette and one focal point per moment.
- **Follow-through / overlapping action:** parts keep moving after the parent stops; children lag.
  Implemented as per-element springs with delay i·Δ (`chainAngles` in `examples/02`) or the AE
  **inertial bounce** expression: `v·amp·sin(freq·t·2π)/e^(decay·t)` → `mg.inertial`.
  Typical values: amp .05, freq 2–3, decay 4–6.
- **Slow in / slow out:** easing.  **Arcs:** natural motion travels on curves.
- **Secondary action:** ticks, particles, background grids that support but don't compete.
- **Timing / exaggeration / appeal:** fewer frames means faster and lighter; push poses past real.
- **Smear frames:** elongated or multiple in-betweens to show speed (since the 1940s). Here:
  motion-blur accumulation at 200–270° shutter, or `fx.smear` for a directional streak. Overuse kills it.

### 1.3 Springs (physics-based motion)
Damped harmonic oscillator step response:
`x(t) = 1 − e^(−ζωt)·(cos ω_d t + (ζω/ω_d) sin ω_d t)`, `ω = 2πf`, `ω_d = ω√(1−ζ²)`.
`mg.spring(t,{freq,damping})`. ζ ≈ .3 bouncy, .45 lively, .7 smooth, 1 critical.

### 1.4 Timing, rhythm, music
- Frames per beat = fps × 60 / BPM (120 BPM @ 30 fps = 15 f; @ 24 fps = 12 f). Check exact beat frames: rounding drift accumulates.
- Holds set rhythm; a hold is as important as a move.
- Stagger / delay: 0.1–0.2 s before a key moment draws attention; cascades use fixed offsets, with organic variation for natural feels.
- Beat-based sync (repeating moves) vs cue-based sync (hits, reveals, transitions).
- Velocity edits: speed ramps (slow → fast) synced to music; "jugg" edits add hard shake + punch-in + glitch per beat.
  Zoom punch: fast on the beat, settle by the next one. Shake should return to rest before the next hit.

## 2. Typography in motion

| Technique | Use | Implementation |
|---|---|---|
| Mask rise / slide-from-baseline | default elegant reveal | clip a rect at the baseline, translate glyphs up with `snap`, stagger 1–3 f |
| Spring slam | beat accents | scale 1.9–2.4 → 1 with `spring`, opacity in 2 f |
| Per-glyph stagger | lively words | `mg.glyphs()` positions + `stagger()` |
| Tracking expand/compress | build tension / "lock in" | `ctx.letterSpacing` animated (`decel` to compress) |
| Weight contrast | rhythm and hierarchy | alternate 200 ↔ 900 weights between beats |
| Outline / solid stack | repetition, echo | `strokeText` rows around one filled row |
| Type-on / write-on | handwriting, code | reveal by character count, or trim paths on stroked letter paths |
| Sine wave per glyph | playful | `sin(t·k − i·φ)` offset by index |
| Skew on speed | velocity feel | `ctx.transform(1,0,skew,1,0,0)` scaled by speed |
| Text on path | logos, badges | `samplePath(d,n)` + rotate per glyph |
| Light sweep | premium finish | second pass of glyphs filled with moving gradient band |
| Reveal from behind object | lockups | clip region = right of the mark's edge |
| Counter roll | data | `outExpo` value, evaluated at `env.frameTime`, tabular layout |

Legibility: sans-serif at heavy weights reads best in motion. Short words big, one idea per screen, ≥ 1 s per ~3 words *(rule of thumb)*.

## 3. Shape & line animation
- **Trim paths:** animate start/end/offset of a stroke (strokes only, not fills). Two trims chasing
  with an offset make the classic "ring chase". `mg.trimPath(ctx,d,start,end,offset)`.
- **Dashed trims:** segmented trails (`setLineDash` before trimming).
- **Shape morph:** resample both shapes to N points (`samplePath`/`circlePts`/`polygonPts`), rotate
  correspondence to minimise travel (`alignPts`), then interpolate (`morphPts`). Common in logo
  animation; best when both shapes share topology.
- **Shockwave ring:** expanding circle, stroke width → 0 and alpha → 0 with `outExpo`.
- **Burst lines:** radial segments whose inner and outer radii ease at slightly different rates.
- **Grids drawing on:** low-contrast detail layer that adds production value without hierarchy cost.
- **Geometric logos** suit assembly, alignment, masking and controlled rotation. **Script logos** suit stroke write-on.

## 4. Transitions catalogue
| Transition | Meaning | Recipe |
|---|---|---|
| Cut on beat | strongest, cleanest | switch sections at `beat(bpm,n)` |
| Color-block / diagonal wipe | graphic, brand | skewed polygon covers (`whip`) then uncovers |
| Mask/matte reveal | new idea emerges | shape used as matte; keep it single-purpose |
| Whip pan | energy, same space | both shots translate W in 6–8 f with `whip`, `fx.smear` by velocity |
| Match cut / graphic match | continuity of idea | same shape, position, motion or colour across the cut |
| Shape morph | transformation | point-aligned morph between symbols |
| Zoom-through | go deeper | scale into centre + `fx.zoomBlur`, flash to next colour |
| Glitch / datamosh | digital disruption | `fx.glitch` band displacement + `fx.rgbSplit`, ≤ 4 frames. True datamosh displaces pixels along optical-flow vectors in a feedback loop |
| Flash frame | drop / impact | 1–2 frames near-white over the cut |
| Luma / gradient wipe | organic | reveal by threshold of a gradient/noise texture |

## 5. 3D motion design
- **Cloner + effectors (C4D MoGraph):** clones parametrically driven by stacked effectors
  (Plain, Random, Step, Formula, Sound, Shader) and **fields** (linear, spherical, noise) evaluated
  top-to-bottom; selections let one cloner carry several animations. Here: `InstancedMesh`, then for
  each clone sum effector contributions → scale / rotation / `setColorAt` (`examples/03`).
- **Geometry-nodes-style loops (Blender):** base instance → duplicates → randomised animation →
  lighting → material; build loops from periodic functions.
- **Isometric:** model in true 3D, render with an orthographic camera (tilt atan(1/√2) = 35.264°,
  yaw 45°). Keeps real light and shadows on a graphic, fixed-view look (`examples/04`).
- **2.5D parallax / multiplane:** flat layers at different Z with a moving camera. Needs enough Z separation;
  near layers look larger. In pure 2D use `mg.project(x,y,z)`.
- **Lighting:** three-point, warm key with soft shadows, cool rim from behind for edge separation,
  hemisphere fill. Fog = aerial perspective. ACES tone mapping for filmic highlight roll-off; disable
  it (NoToneMapping) for flat brand-accurate graphics.
- **Materials:** chrome/metal needs something to reflect, so PMREM a studio scene of emissive panels.
  Plastic: roughness .3–.5. Clay: roughness .9, no metalness.
- **Metaballs / liquid blobs, particles:** popular paired with gradients, grain and glitch. Particles
  here: closed-form ballistic with drag `d = v/k·(1−e^(−kt))` plus gravity `½gt²`, so they stay deterministic.
- **2D/3D hybrid** (the 2026 trend): 3D hero objects inside 2D graphic layouts, with 2D labels pinned to 3D anchors via `vector.project(camera)`.

## 6. Compositing & finishing
- **Motion blur:** shutter angle = fraction of frame time exposed. 180° = ½ frame (film standard).
  Centre the shutter (phase = −angle/2). Too few samples leave echoes; ~12 samples is a sensible balance for fast moves.
- **Bloom:** threshold, then blur at multiple radii, then screen back on top. A "finisher" effect.
- **Chromatic aberration:** RGB separation growing toward the frame edges (lateral CA).
- **Vignette:** steers attention; off-centre toward a light source.
- **Grain:** per-channel or mono, animated per frame, applied **last** (it simulates the film base).
- **Halation:** soft bleed around bright edges (bloom on a warm-tinted threshold).
- **Stylised imperfection:** deliberate grain, CA and lens artefacts make clean CG feel tactile.

## 7. Sound design for motion
- Layer impacts: low (sub/kick), mid (body), high (crack/noise). `impact` = pitch-dropping sine + noise crack.
- Whooshes lead the move slightly; `audio.py` centres them on the transition.
- Risers build with rising filter/pitch and **end** on the hit.
- Hits sit on the contact frame. Nudge the animation until transient and contact feel simultaneous.
- Keep accents sparse (≈ 3–5 per short sequence); the music bed carries rhythm.

## 8. Platforms & formats
- 9:16 1080×1920 (Reels/TikTok/Shorts), 1:1 1080×1080 (feed), 16:9 1920×1080 (YouTube, decks), 4:5 1080×1350 (feed).
- 9:16 safe zone *(varies by platform; check overlays)*: avoid ~220 px top and ~420 px bottom; keep
  text in a central ≈ 900–1010 × 1160–1280 box.
- Sound-off is the norm: tell the story in type. Hook in the first 1–2 s. Loops increase rewatch.
- Vertical motion (up/down) reads strongly in 9:16; avoid lots of fast lateral motion in narrow frames.

## 9. Process
Brief (goals, deliverables, refs, style guide) → concept → script/beat sheet → **styleframes** (key
moments, side-by-side variations) → storyboard → **animatic** (timing check) → animation →
compositing → sound → review → render → delivery. Even a cheap animatic (stills over the music) catches timing problems early.

## 10. Trends (2025–2026, agency consensus)
2D/3D hybrids; tactile/hand-made and collage textures; kinetic typography as a core social format;
vertical-first short loops; sound-off design; grain/gradients/glitch; AI as a production aid, not the
taste layer. Restraint and brand fit beat flashy templates.

---

## Sources
- School of Motion: six essential transitions, match cuts, stacking MoGraph effectors, squash & stretch, automatic follow-through, 5-step blueprint: schoolofmotion.com/blog/…
- PremiumBeat, *Animation easing, anticipation, follow-through*: premiumbeat.com/blog/animation-easing-anticipation-follow-through/
- Figma, *Principles in motion*: figma.com/blog/principles-in-motion/
- Adobe, *Adjusting keyframes for dynamic movement*; Trim paths / multiline patterns: adobe.com/learn/after-effects/…
- Rive docs, speed graph / graph editor: rive.app/docs/editor/animate-mode/speed-graph
- Material Design 3 motion tokens (material-components-android Motion.md); m1.material.io/motion/duration-easing
- Maxon Cinema 4D docs, MoGraph basics and Cloner Object: maxon.net/cinema-4d/features/mograph-basics, help.maxon.net
- Novedge C4D tips (field-driven effectors, cloner workflow)
- BlenderNation / 3dart.it geometry-nodes looping tutorials
- Wikipedia: Kinetic typography; Smear frame. Bloop Animation, *The art of smear frames*
- Creative Bloq, Linearity, SVGator kinetic-typography guides and example galleries
- Animoplex inertial-bounce gist; Envato Tuts+ inertial bounce tutorial
- Peachpit, timing animation to music; IADT paper *A Brief History of Sound and Musical Timing in Animation*
- Pixar RenderMan, Foundry Nuke, Blender manual, ProVideoCoalition: motion blur / shutter
- Cycling '74 pass effects (bloom, grain order); Unreal / Unity HDRP post-process docs; No Film School, *Make it look worse on purpose*
- Buck, *Moshing* (datamosh); Codrops, real-time datamosh in Three.js (2026); GarageFarm, isometric animation
- Vertical safe-zone guides (Tella, Syllaby, Ignite Social), MyCom vertical video best practices
- Videomaker, Pixflow, Ableton: sound design for motion and trailers
- Remotion vs Motion Canvas comparisons (code-driven video)
- 2026 trend roundups: Tangence, GarageFarm, Bottle Rocket, Genesis, Motion-Lab
- Milanote / Boords / Sarah Beth Morgan: styleframes, storyboards, animatics
