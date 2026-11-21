// EDIT 01 — "Kinetic Type" · 9:16 social · 120 BPM · 10 s
// Techniques: beat-locked cuts (1 beat = 0.5 s = 15 f), mask-rise reveals, spring overshoot slams,
// per-glyph stagger, tracking expansion, color-block wipe transitions, beat pump, trim-path underline,
// camera shake on the drop, motion blur (180°), grain/vignette/CA finishing.
import * as mg from '/lib/mg.js';
const { seg, spring, beat, stagger, palettes, clamp, lerp } = mg;

const P = palettes.electric;
const BPM = 120, B = (n) => beat(BPM, n); // B(1) = 0.5 s
const W = 1080, H = 1920;
const FONT = (w, px) => `${w} ${px}px "Inter Display", "Inter", "DejaVu Sans", sans-serif`;

// Draw a word that rises out of a hard mask line (the classic "mask reveal"), per-glyph staggered.
function maskRise(ctx, word, x, y, size, t, start, { weight = 900, color = P.ink, each = 0.035, dur = 0.45, tracking = 0, exit = null, ease = 'snap' } = {}) {
  ctx.font = FONT(weight, size);
  ctx.letterSpacing = '0px';
  const { glyphs } = mg.glyphs(ctx, word, tracking);
  const top = y - size * 0.78, h = size * 1.02;
  ctx.save();
  ctx.beginPath(); ctx.rect(0, top, W, h); ctx.clip();
  ctx.fillStyle = color; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'center';
  glyphs.forEach((g, i) => {
    const k = seg(t, start + stagger(i, glyphs.length, each), dur, ease);
    let dy = (1 - k) * h * 1.05;
    if (exit !== null) dy -= seg(t, exit + stagger(i, glyphs.length, each * 0.6), dur * 0.8, 'accel') * h * 1.05;
    ctx.fillText(g.ch, x + g.cx, y + dy);
  });
  ctx.restore();
}

// Big word that slams in with a spring overshoot (scale) on a beat.
function slam(ctx, word, x, y, size, t, start, { color = P.ink, weight = 900, freq = 2.6, damping = 0.38, skew = 0 } = {}) {
  if (t < start) return;
  const s = spring(t - start, { freq, damping });
  const sc = lerp(2.4, 1, s);
  ctx.save(); ctx.translate(x, y); ctx.scale(sc, sc); ctx.transform(1, 0, skew, 1, 0, 0);
  ctx.globalAlpha = clamp((t - start) / 0.06);
  ctx.font = FONT(weight, size); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = color;
  ctx.fillText(word, 0, 0); ctx.restore(); ctx.globalAlpha = 1;
}

// Diagonal color-block wipe (cover → reveal). Returns coverage of the current frame.
function wipe(ctx, t, start, color, dir = 1, dur = B(1)) {
  const a = seg(t, start, dur * 0.5, 'whip'), b = seg(t, start + dur * 0.5, dur * 0.5, 'whip');
  if (a <= 0 || b >= 1) return;
  const skew = 380;
  const x0 = lerp(-W - skew, 0, a) * dir, x1 = lerp(0, W + skew, b) * dir;
  ctx.save(); ctx.fillStyle = color; ctx.beginPath();
  const L = dir > 0 ? x1 : x0, R = dir > 0 ? x0 + W + skew : x1 + W + skew;
  ctx.moveTo(L, 0); ctx.lineTo(R, 0); ctx.lineTo(R - skew, H); ctx.lineTo(L - skew, H); ctx.closePath(); ctx.fill(); ctx.restore();
}

const SHOTS = [0, B(4), B(8), B(12), B(16)]; // shot boundaries on bar lines: 0, 2, 4, 6, 8 s

export default {
  title: 'Kinetic Type',
  width: W, height: H, fps: 30, duration: 10,
  motionBlur: { samples: 12, shutter: 180 },
  finish: { grain: 0.09, vignette: 0.45, ca: 5 },
  audio: {
    bpm: BPM, start: 0, kick: 'x...x...x...x...', clap: '....x.......x...', hat: '..x...x...x...x.',
    bass: 'x..x..x...x..x..', bassNotes: ['E1', 'E1', 'C2', 'D2'], musicFrom: 0, musicTo: 9.4,
    events: [
      { t: 2, type: 'whoosh', dur: 0.4 }, { t: 4, type: 'whoosh', dur: 0.4 }, { t: 6, type: 'whoosh', dur: 0.4 },
      { t: 4, type: 'riser', dur: 2 }, { t: 6, type: 'impact' }, { t: 8, type: 'whoosh', dur: 0.5 },
      { t: 8.25, type: 'sub' }, { t: 8.9, type: 'shimmer' }, { t: 0.02, type: 'click' },
    ],
  },
  render(t, { ctx }) {
    // Global beat pump & drop shake
    const pump = mg.beatPulse(t, BPM, 9) * (t > 6 && t < 8 ? 1 : 0.35);
    const sh = mg.shake(t, 6, { amp: 26, freq: 18, decay: 5, rot: 0.02 });
    const bg = t < SHOTS[1] ? P.bg : t < SHOTS[2] ? P.a : t < SHOTS[3] ? P.bg : t < SHOTS[4] ? P.b : P.bg;
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
    ctx.save();
    ctx.translate(W / 2 + sh.x, H / 2 + sh.y); ctx.rotate(sh.r); ctx.scale(1 + pump * 0.025, 1 + pump * 0.025); ctx.translate(-W / 2, -H / 2);

    // Shot 1 (0–2 s): "EVERY / FRAME / COUNTS" stacked mask rises on beats
    if (t < SHOTS[1]) {
      const ex = SHOTS[1] - 0.35;
      maskRise(ctx, 'EVERY', W / 2, 760, 220, t, 0.05, { exit: ex });
      maskRise(ctx, 'FRAME', W / 2, 990, 220, t, B(1), { color: P.a, exit: ex + 0.05 });
      maskRise(ctx, 'COUNTS', W / 2, 1220, 220, t, B(2), { exit: ex + 0.1 });
      // tick marks counting frames (detail layer / secondary motion)
      for (let i = 0; i < 24; i++) {
        const k = seg(t, 0.2 + i * 0.03, 0.25, 'outExpo') * (1 - seg(t, ex, 0.3, 'accel'));
        ctx.fillStyle = i % 6 === 0 ? P.a : P.ink; ctx.globalAlpha = 0.85;
        ctx.fillRect(120 + i * 36, 1330, 6, (i % 6 === 0 ? 46 : 24) * k);
      }
      ctx.globalAlpha = 1;
      ctx.font = FONT(500, 30); ctx.fillStyle = P.ink; ctx.textAlign = 'left'; ctx.letterSpacing = '6px';
      ctx.globalAlpha = seg(t, 0.6, 0.3) * (1 - seg(t, ex, 0.2));
      ctx.fillText(`F ${String(Math.floor(t * 30)).padStart(3, '0')}`, 120, 1440); ctx.globalAlpha = 1; ctx.letterSpacing = '0px';
    }

    // Shot 2 (2–4 s): on red — single-word slams, one per beat, alternating weight
    if (t >= SHOTS[1] && t < SHOTS[2]) {
      const words = ['EASE', 'IN.', 'EASE', 'OUT.'];
      const i = clamp(Math.floor((t - SHOTS[1]) / B(1)), 0, 3);
      slam(ctx, words[i], W / 2, H / 2 - 40, i % 2 ? 300 : 260, t, SHOTS[1] + i * B(1), { color: i % 2 ? P.bg : P.ink, weight: i % 2 ? 900 : 200 });
      // speed graph doodle under the word — trim path draws on each beat
      const local = (t - SHOTS[1]) % B(1);
      ctx.strokeStyle = P.bg; ctx.lineWidth = 8; ctx.lineCap = 'round';
      const d = i < 2 ? 'M 240 1180 C 420 1180 560 1180 840 1060' : 'M 240 1060 C 520 1180 660 1180 840 1180';
      mg.trimPath(ctx, d, 0, seg(local, 0.05, 0.35, 'outExpo'));
    }

    // Shot 3 (4–6 s): tracking expansion + outline/solid stack (riser build)
    if (t >= SHOTS[2] && t < SHOTS[3]) {
      const k = seg(t, SHOTS[2], 2, 'inQuad');
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      for (let r = -4; r <= 4; r++) {
        const y = H / 2 + r * 150 * lerp(0.6, 1, seg(t, SHOTS[2], 0.6, 'outExpo'));
        ctx.font = FONT(900, 150); ctx.letterSpacing = `${lerp(-6, 50, k) * (1 - Math.abs(r) * 0.08)}px`;
        if (r === 0) { ctx.fillStyle = P.a; ctx.fillText('TIMING', W / 2, y); }
        else { ctx.strokeStyle = P.ink; ctx.globalAlpha = 0.9 - Math.abs(r) * 0.18; ctx.lineWidth = 2.5; ctx.strokeText('TIMING', W / 2 + Math.sin(t * 3 + r) * 20 * k, y); }
      }
      ctx.globalAlpha = 1; ctx.letterSpacing = '0px';
    }

    // Shot 4 (6–8 s): THE DROP — blue, huge word, per-beat color flip + shake
    if (t >= SHOTS[3] && t < SHOTS[4]) {
      const b = Math.floor((t - SHOTS[3]) / B(1));
      const words = ['IS', 'EVERY', 'THING.', 'THING.'];
      slam(ctx, words[b] || 'THING.', W / 2, H / 2, b === 1 ? 250 : 270, t, SHOTS[3] + b * B(1), { color: b % 2 ? P.c : P.ink, freq: 3, damping: 0.32, skew: -0.12 });
      // radial burst lines on each beat
      const lt = (t - SHOTS[3]) % B(1);
      ctx.strokeStyle = P.c; ctx.lineWidth = 6; ctx.lineCap = 'round';
      for (let i = 0; i < 16; i++) {
        const a = (i / 16) * mg.TAU + b;
        const r0 = lerp(260, 620, seg(lt, 0, 0.35, 'outExpo')), r1 = lerp(300, 720, seg(lt, 0.02, 0.3, 'outCubic'));
        if (r1 - r0 < 2) continue;
        ctx.beginPath(); ctx.moveTo(W / 2 + Math.cos(a) * r0, H / 2 + Math.sin(a) * r0); ctx.lineTo(W / 2 + Math.cos(a) * r1, H / 2 + Math.sin(a) * r1); ctx.stroke();
      }
    }

    // Shot 5 (8–10 s): lockup — kicker, title rise, underline draw-on, hold
    if (t >= SHOTS[4]) {
      const s = SHOTS[4];
      ctx.font = FONT(500, 34); ctx.fillStyle = P.a; ctx.textAlign = 'center'; ctx.letterSpacing = `${lerp(30, 12, seg(t, s + 0.1, 0.9, 'decel'))}px`;
      ctx.globalAlpha = seg(t, s + 0.1, 0.4); ctx.fillText('A MOTION STUDY', W / 2, 780); ctx.globalAlpha = 1; ctx.letterSpacing = '0px';
      maskRise(ctx, 'MOVE', W / 2, 1010, 260, t, s + 0.2, { each: 0.045, dur: 0.6 });
      maskRise(ctx, 'WITH', W / 2, 1250, 260, t, s + 0.32, { each: 0.045, dur: 0.6, weight: 200 });
      maskRise(ctx, 'INTENT', W / 2, 1490, 260, t, s + 0.44, { each: 0.045, dur: 0.6, color: P.a });
      ctx.strokeStyle = P.ink; ctx.lineWidth = 10; ctx.lineCap = 'round';
      mg.trimPath(ctx, 'M 150 1580 L 930 1580', 0, seg(t, s + 0.9, 0.7, 'snap'));
      ctx.fillStyle = P.c; const dk = spring(t - (s + 1.5), { freq: 2.5, damping: 0.4 });
      ctx.beginPath(); ctx.arc(930, 1580, 18 * dk, 0, mg.TAU); ctx.fill();
    }
    ctx.restore();

    // Transitions sit above everything (outside the shake)
    wipe(ctx, t, SHOTS[1] - B(0.5), P.ink, 1);
    wipe(ctx, t, SHOTS[2] - B(0.5), P.c, -1);
    wipe(ctx, t, SHOTS[3] - B(0.5), P.a, 1);
    wipe(ctx, t, SHOTS[4] - B(0.5), P.ink, -1);
    // Flash frame on the drop
    if (t >= 6 && t < 6 + 2 / 30) { ctx.fillStyle = 'rgba(255,255,255,0.85)'; ctx.fillRect(0, 0, W, H); }
    // Fade to black tail
    ctx.fillStyle = `rgba(0,0,0,${seg(t, 9.5, 0.5)})`; ctx.fillRect(0, 0, W, H);
  },
};
