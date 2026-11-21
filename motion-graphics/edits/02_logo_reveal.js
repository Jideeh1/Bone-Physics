// EDIT 02 — "Logo Reveal" · 16:9 · 8 s · light theme
// Techniques: anticipation squash → pop, shockwave ring, dual trim-path ring chase, circle→hexagon
// shape morph (point-aligned), 3-bone chain with follow-through / overlapping action (per-joint lagged
// damped springs), mark-slides-out + wordmark revealed from behind the mark (track matte),
// tracking-compress tagline, specular light sweep clipped to type, secondary "breathing" on hold.
import * as mg from '/lib/mg.js';
const { seg, spring, lerp, clamp, TAU } = mg;

const W = 1920, H = 1080, P = mg.palettes.paper;
const FONT = (w, px) => `${w} ${px}px "Inter Display", "Inter", sans-serif`;
const N = 120;
const CIRCLE = mg.circlePts(N, 150);
const HEX = mg.alignPts(CIRCLE, mg.polygonPts(N, 6, 165, -Math.PI / 2));

// Chain of bones: angles driven by lagged under-damped springs → follow-through & overlap.
function chainAngles(t, start) {
  const base = [-0.661, -1.762, 1.803]; // rest pose (relative angles)
  return base.map((a, i) => {
    const lt = t - start - i * 0.09;                     // each child lags its parent
    const s = spring(lt, { freq: 1.6 + i * 0.25, damping: 0.32 });
    const swing = (1 - s) * (1.6 - i * 0.2);             // start swung out, settle with overshoot
    const breathe = Math.sin(t * 1.6 - i * 0.7) * 0.035 * seg(t, 5.2, 1);
    return a + swing * (i === 0 ? -1 : 1) + breathe;
  });
}

function capsule(ctx, x0, y0, x1, y1, r) {
  const a = Math.atan2(y1 - y0, x1 - x0);
  ctx.beginPath(); ctx.arc(x0, y0, r, a + Math.PI / 2, a - Math.PI / 2); ctx.arc(x1, y1, r, a - Math.PI / 2, a + Math.PI / 2); ctx.closePath();
}

function drawMark(ctx, t, cx, cy, scale) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(scale, scale);
  // Ring: two trim paths chasing each other, then locking into one closed shape
  const ringD = 'M 0 -150 A 150 150 0 1 1 -0.01 -150 Z';
  const morph = seg(t, 2.7, 0.7, 'snap');
  ctx.lineWidth = 18; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  if (morph <= 0) {
    const draw = seg(t, 0.75, 1.1, 'snap'), off = seg(t, 0.75, 1.6, 'outCubic') * 0.75;
    ctx.strokeStyle = P.ink; mg.trimPath(ctx, ringD, 0, draw * 1.0, off);
    ctx.strokeStyle = P.a; mg.trimPath(ctx, ringD, 0, clamp(draw * 0.25 - seg(t, 1.6, 0.4) * 0.25), off + 0.5);
  } else {
    const pts = mg.morphPts(CIRCLE, HEX, morph);
    const rot = (1 - spring(t - 2.7, { freq: 1.4, damping: 0.45 })) * 0.5;
    ctx.save(); ctx.rotate(rot); ctx.strokeStyle = P.ink; mg.poly(ctx, pts); ctx.stroke(); ctx.restore();
  }
  // Bones
  const appear = seg(t, 1.15, 0.25, 'outQuad');
  if (appear > 0) {
    const ang = chainAngles(t, 1.15), L = [114, 106, 86];
    let x = -50, y = 90, a = 0; const joints = [[x, y]];
    ang.forEach((da, i) => { a += da; x += Math.cos(a) * L[i] * appear; y += Math.sin(a) * L[i] * appear; joints.push([x, y]); });
    ctx.fillStyle = P.ink;
    for (let i = 0; i < 3; i++) { capsule(ctx, ...joints[i], ...joints[i + 1], 14); ctx.fill(); }
    joints.forEach(([jx, jy], i) => {
      const pop = spring(t - 1.2 - i * 0.1, { freq: 3, damping: 0.4 });
      ctx.fillStyle = i === 3 ? P.a : P.bg; ctx.beginPath(); ctx.arc(jx, jy, (i === 3 ? 26 : 20) * pop, 0, TAU); ctx.fill();
      ctx.strokeStyle = P.ink; ctx.lineWidth = 8; ctx.stroke();
    });
  }
  ctx.restore();
}

export default {
  title: 'Logo Reveal',
  width: W, height: H, fps: 30, duration: 8,
  motionBlur: { samples: 10, shutter: 200 },
  finish: { grain: 0.05, vignette: 0.18 },
  audio: {
    bpm: 0,
    events: [
      { t: 0.5, type: 'riser', dur: 0.5 }, { t: 0.62, type: 'pop' }, { t: 0.65, type: 'sub' },
      { t: 1.0, type: 'whoosh', dur: 0.8 }, { t: 1.25, type: 'click' }, { t: 1.35, type: 'click' }, { t: 1.45, type: 'click' },
      { t: 2.85, type: 'pop' }, { t: 3.4, type: 'whoosh', dur: 0.6 }, { t: 3.75, type: 'impact', gain: 0.7 },
      { t: 4.9, type: 'shimmer' },
    ],
  },
  render(t, { ctx }) {
    ctx.fillStyle = P.bg; ctx.fillRect(0, 0, W, H);
    // Background grid draws on (detail layer, lower contrast = lower hierarchy)
    ctx.strokeStyle = 'rgba(20,20,20,0.06)'; ctx.lineWidth = 1.5;
    for (let i = 0; i <= 24; i++) {
      const k = seg(t, 0.2 + i * 0.02, 0.8, 'outExpo');
      ctx.beginPath(); ctx.moveTo(i * 80, 0); ctx.lineTo(i * 80, H * k); ctx.stroke();
      if (i <= 13) { ctx.beginPath(); ctx.moveTo(0, i * 80 + 20); ctx.lineTo(W * k, i * 80 + 20); ctx.stroke(); }
    }

    // Phase A: anticipation dot (0–0.7 s): appears, squashes down, pops
    const slide = seg(t, 3.2, 0.9, 'snap');
    const cx = lerp(W / 2, 470, slide), cy = H / 2;
    if (t < 0.75) {
      const grow = spring(t - 0.1, { freq: 2.4, damping: 0.5 });
      const sq = seg(t, 0.35, 0.25, 'inCubic'); // anticipation: squash before release
      ctx.fillStyle = P.a; ctx.beginPath(); ctx.ellipse(cx, cy + sq * 10, 26 * grow * (1 + sq * 0.5), 26 * grow * (1 - sq * 0.4), 0, 0, TAU); ctx.fill();
    }
    // Shockwave ring at the pop
    const sw = seg(t, 0.62, 0.7, 'outExpo');
    if (sw > 0 && sw < 1) { ctx.strokeStyle = mg.rgba(P.a, 1 - sw); ctx.lineWidth = 40 * (1 - sw) + 1; ctx.beginPath(); ctx.arc(cx, cy, 30 + sw * 520, 0, TAU); ctx.stroke(); }
    if (t >= 0.62) {
      const sc = lerp(0.6, 1, spring(t - 0.62, { freq: 1.8, damping: 0.5 })) * lerp(1, 0.92, slide);
      drawMark(ctx, t, cx, cy, sc);
    }

    // Wordmark: revealed from behind the mark (matte = everything right of the mark's edge)
    if (t > 3.2) {
      ctx.save();
      ctx.beginPath(); ctx.rect(cx + 175, 0, W, H); ctx.clip();
      ctx.font = FONT(800, 136); ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left'; ctx.fillStyle = P.ink;
      const word = 'BONE PHYSICS';
      const { glyphs } = mg.glyphs(ctx, word, -2);
      const x0 = 690;
      const drawWord = () => glyphs.forEach((g, i) => {
        const k = seg(t, 3.35 + mg.stagger(i, glyphs.length, 0.03), 0.8, 'snap');
        ctx.fillText(g.ch, lerp(x0 - 420, x0 + g.x, k), H / 2 + 50);
      });
      drawWord();
      // Specular light sweep: second pass of the same glyphs filled with a moving gradient band
      const sweep = seg(t, 4.7, 0.9, 'inOutSine');
      if (sweep > 0 && sweep < 1) {
        const sx = lerp(x0 - 300, x0 + 1300, sweep);
        const g = ctx.createLinearGradient(sx - 140, 0, sx + 140, 0);
        g.addColorStop(0, 'rgba(255,90,31,0)'); g.addColorStop(0.5, 'rgba(255,170,120,0.95)'); g.addColorStop(1, 'rgba(255,90,31,0)');
        ctx.fillStyle = g; drawWord();
      }
      ctx.restore();
      // Tagline: tracking compresses as it fades in (feels like it "locks" into place)
      const tk = seg(t, 4.2, 1.1, 'decel');
      ctx.font = FONT(500, 34); ctx.letterSpacing = `${lerp(40, 14, tk)}px`; ctx.fillStyle = mg.rgba(P.ink, tk * 0.75);
      ctx.fillText('PROCEDURAL  SKELETAL  MOTION', x0 + 6, H / 2 + 125); ctx.letterSpacing = '0px';
      // Accent rule draws on
      ctx.strokeStyle = P.a; ctx.lineWidth = 6; ctx.lineCap = 'round';
      mg.trimPath(ctx, `M ${x0 + 6} ${H / 2 - 115} L ${x0 + 130} ${H / 2 - 115}`, 0, seg(t, 4.0, 0.6, 'snap'));
    }
    // Outro fade
    ctx.fillStyle = mg.rgba(P.bg, seg(t, 7.4, 0.6, 'inQuad')); ctx.fillRect(0, 0, W, H);
  },
};
