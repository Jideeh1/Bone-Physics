// mg.js — motion graphics toolkit (browser ES module, no deps).
// Everything is a pure function of time `t` (seconds) so frames are deterministic,
// can be rendered out of order, and support sub-frame motion-blur sampling.

// ───────────────────────── math ─────────────────────────
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const invLerp = (a, b, x) => (b === a ? 0 : (x - a) / (b - a));
export const remap = (x, a, b, c, d, ease = null) => {
  const k = clamp(invLerp(a, b, x));
  return lerp(c, d, ease ? ease(k) : k);
};
export const mix = (a, b, k) =>
  Array.isArray(a) ? a.map((v, i) => lerp(v, b[i], k)) : lerp(a, b, k);
export const TAU = Math.PI * 2;
export const deg = (d) => (d * Math.PI) / 180;
export const fract = (x) => x - Math.floor(x);
export const smoothstep = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };

// ─────────────────────── seeded random ──────────────────────
export function rng(seed = 1) {
  let s = seed >>> 0;
  return () => {
    s |= 0; s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export const hash = (n) => fract(Math.sin(n * 127.1 + 311.7) * 43758.5453);

// ───────────────────────── easing ─────────────────────────
// Cubic-bezier solver identical in spirit to CSS / After Effects influence handles.
export function bezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = (t) => ((ax * t + bx) * t + cx) * t;
  const sy = (t) => ((ay * t + by) * t + cy) * t;
  const dx = (t) => (3 * ax * t + 2 * bx) * t + cx;
  return (x) => {
    if (x <= 0) return 0; if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 8; i++) { const e = sx(t) - x; const d = dx(t); if (Math.abs(e) < 1e-6) return sy(t); if (Math.abs(d) < 1e-6) break; t -= e / d; }
    let lo = 0, hi = 1; t = x;
    for (let i = 0; i < 30; i++) { const v = sx(t); if (Math.abs(v - x) < 1e-6) break; if (x > v) lo = t; else hi = t; t = (lo + hi) / 2; }
    return sy(t);
  };
}
const inOut = (fin) => (x) => (x < 0.5 ? fin(2 * x) / 2 : 1 - fin(2 - 2 * x) / 2);
const out = (fin) => (x) => 1 - fin(1 - x);
const pow = (p) => (x) => Math.pow(x, p);
const c1 = 1.70158, c3 = c1 + 1;
const bounceOut = (x) => {
  const n = 7.5625, d = 2.75;
  if (x < 1 / d) return n * x * x;
  if (x < 2 / d) return n * (x -= 1.5 / d) * x + 0.75;
  if (x < 2.5 / d) return n * (x -= 2.25 / d) * x + 0.9375;
  return n * (x -= 2.625 / d) * x + 0.984375;
};
export const ease = {
  linear: (x) => x,
  inQuad: pow(2), outQuad: out(pow(2)), inOutQuad: inOut(pow(2)),
  inCubic: pow(3), outCubic: out(pow(3)), inOutCubic: inOut(pow(3)),
  inQuart: pow(4), outQuart: out(pow(4)), inOutQuart: inOut(pow(4)),
  inQuint: pow(5), outQuint: out(pow(5)), inOutQuint: inOut(pow(5)),
  inSine: (x) => 1 - Math.cos((x * Math.PI) / 2), outSine: (x) => Math.sin((x * Math.PI) / 2), inOutSine: (x) => -(Math.cos(Math.PI * x) - 1) / 2,
  inExpo: (x) => (x === 0 ? 0 : Math.pow(2, 10 * x - 10)), outExpo: (x) => (x === 1 ? 1 : 1 - Math.pow(2, -10 * x)),
  inOutExpo: (x) => (x === 0 ? 0 : x === 1 ? 1 : x < 0.5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2),
  inCirc: (x) => 1 - Math.sqrt(1 - x * x), outCirc: (x) => Math.sqrt(1 - Math.pow(x - 1, 2)),
  inOutCirc: (x) => (x < 0.5 ? (1 - Math.sqrt(1 - 4 * x * x)) / 2 : (Math.sqrt(1 - Math.pow(-2 * x + 2, 2)) + 1) / 2),
  inBack: (x) => c3 * x * x * x - c1 * x * x, outBack: (x) => 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2),
  inOutBack: (x) => { const c2 = c1 * 1.525; return x < 0.5 ? (Math.pow(2 * x, 2) * ((c2 + 1) * 2 * x - c2)) / 2 : (Math.pow(2 * x - 2, 2) * ((c2 + 1) * (x * 2 - 2) + c2) + 2) / 2; },
  outElastic: (x) => (x === 0 ? 0 : x === 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - 0.75) * (TAU / 3)) + 1),
  outBounce: bounceOut, inBounce: (x) => 1 - bounceOut(1 - x),
  // Motion-design presets
  easyEase: bezier(0.33, 0, 0.67, 1),          // AE F9 (33% influence)
  smooth: bezier(0.65, 0, 0.35, 1),            // strong in-out, "graph editor S-curve"
  snap: bezier(0.8, 0, 0.1, 1),                // heavy in, very heavy out — the "pro" mograph curve
  whip: bezier(0.9, 0, 0.1, 1),                // for whip transitions: sits, flies, sits
  decel: bezier(0.05, 0.7, 0.1, 1),            // Material 3 emphasized-decelerate (entrances)
  accel: bezier(0.3, 0, 0.8, 0.15),            // Material 3 emphasized-accelerate (exits)
  standard: bezier(0.2, 0, 0, 1),              // Material 3 standard
};
export const getEase = (e) => (typeof e === 'function' ? e : ease[e || 'easyEase'] || ease.easyEase);

// ───────────────────── timing primitives ─────────────────────
// Eased 0→1 progress of a segment starting at `start` lasting `dur`.
export const seg = (t, start, dur, e = 'easyEase') => getEase(e)(clamp((t - start) / dur));
// Linear progress (no easing).
export const prog = (t, start, dur) => clamp((t - start) / dur);
// Offset per index for cascades. `from`: 'start' | 'end' | 'center' | 'random'.
export function stagger(i, n, each, from = 'start', seed = 7) {
  if (from === 'end') return (n - 1 - i) * each;
  if (from === 'center') return Math.abs(i - (n - 1) / 2) * each;
  if (from === 'random') return hash(i * 13.37 + seed) * (n - 1) * each;
  return i * each;
}
// Beat clock. bpm → seconds.
export const beat = (bpm, b) => (60 / bpm) * b;
// Sharp attack, exponential release pulse on every beat (0..1). Use to drive scale/glow "pumps".
export function beatPulse(t, bpm, decay = 8, offset = 0, every = 1) {
  const p = 60 / bpm * every; const local = ((t - offset) % p + p) % p;
  return t < offset ? 0 : Math.exp(-local * decay);
}

// Keyframe track: [{t, v, e}] — `e` is the ease INTO that key. v may be number or array.
export function track(keys) {
  return (t) => {
    if (t <= keys[0].t) return keys[0].v;
    for (let i = 1; i < keys.length; i++) {
      const a = keys[i - 1], b = keys[i];
      if (t <= b.t) return mix(a.v, b.v, getEase(b.e)((t - a.t) / (b.t - a.t)));
    }
    return keys[keys.length - 1].v;
  };
}

// ─────────────────────── physics-y motion ───────────────────────
// Critically/under-damped spring step response 0→1 (settles with overshoot when damping<1).
export function spring(t, { freq = 2.2, damping = 0.45 } = {}) {
  if (t <= 0) return 0;
  const w = TAU * freq, z = damping;
  if (z >= 1) return 1 - Math.exp(-w * t) * (1 + w * t);
  const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
}
// Spring segment: like seg() but with physical overshoot.
export const springSeg = (t, start, opts) => spring(t - start, opts);
// "Inertial bounce" (the classic AE expression): damped sine after a move stops.
export const inertial = (tSinceStop, velocity, amp = 0.05, freq = 2.5, decay = 5) =>
  tSinceStop <= 0 ? 0 : (velocity * amp * Math.sin(freq * tSinceStop * TAU)) / Math.exp(decay * tSinceStop);
// Squash & stretch preserving volume from speed (px/s). Returns [sx, sy] along motion axis.
export function squash(speed, k = 0.0006, max = 0.45) {
  const s = Math.min(max, Math.abs(speed) * k);
  return [1 + s, 1 / (1 + s)];
}
// Numerical velocity of any f(t).
export const vel = (f, t, h = 1 / 240) => (f(t + h) - f(t - h)) / (2 * h);

// ───────────────────────── noise ─────────────────────────
const P = new Uint8Array(512);
{ const r = rng(1337); const p = [...Array(256).keys()]; for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; } for (let i = 0; i < 512; i++) P[i] = p[i & 255]; }
const G3 = [[1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0],[1,0,1],[-1,0,1],[1,0,-1],[-1,0,-1],[0,1,1],[0,-1,1],[0,1,-1],[0,-1,-1]];
// 3D simplex noise, range ≈ [-1, 1].
export function noise3(x, y, z) {
  const F3 = 1 / 3, G = 1 / 6;
  const s = (x + y + z) * F3; const i = Math.floor(x + s), j = Math.floor(y + s), k = Math.floor(z + s);
  const t0 = (i + j + k) * G; const x0 = x - i + t0, y0 = y - j + t0, z0 = z - k + t0;
  let i1, j1, k1, i2, j2, k2;
  if (x0 >= y0) { if (y0 >= z0) { i1=1;j1=0;k1=0;i2=1;j2=1;k2=0; } else if (x0 >= z0) { i1=1;j1=0;k1=0;i2=1;j2=0;k2=1; } else { i1=0;j1=0;k1=1;i2=1;j2=0;k2=1; } }
  else { if (y0 < z0) { i1=0;j1=0;k1=1;i2=0;j2=1;k2=1; } else if (x0 < z0) { i1=0;j1=1;k1=0;i2=0;j2=1;k2=1; } else { i1=0;j1=1;k1=0;i2=1;j2=1;k2=0; } }
  const pts = [[x0, y0, z0, 0, 0, 0], [x0 - i1 + G, y0 - j1 + G, z0 - k1 + G, i1, j1, k1], [x0 - i2 + 2 * G, y0 - j2 + 2 * G, z0 - k2 + 2 * G, i2, j2, k2], [x0 - 1 + 3 * G, y0 - 1 + 3 * G, z0 - 1 + 3 * G, 1, 1, 1]];
  let n = 0; const ii = i & 255, jj = j & 255, kk = k & 255;
  for (const [px, py, pz, a, b, c] of pts) {
    let tt = 0.6 - px * px - py * py - pz * pz; if (tt < 0) continue;
    const g = G3[P[ii + a + P[jj + b + P[kk + c]]] % 12]; tt *= tt; n += tt * tt * (g[0] * px + g[1] * py + g[2] * pz);
  }
  return 32 * n;
}
export const noise2 = (x, y) => noise3(x, y, 0.5);
export const noise1 = (x) => noise3(x, 0.31, 0.77);
export function fbm(x, y, z = 0, oct = 4) { let a = 0.5, f = 1, s = 0; for (let i = 0; i < oct; i++) { s += a * noise3(x * f, y * f, z * f); a *= 0.5; f *= 2; } return s; }
// AE-style wiggle(freq, amp) — smooth, seedable.
export const wiggle = (t, freq, amp, seed = 0) => noise1(t * freq + seed * 17.13) * amp;
// Seamless loop noise: travels a circle in noise space so value(t)==value(t+period).
export function loopNoise(t, period, radius = 1, seed = 0) { const a = (t / period) * TAU; return noise3(Math.cos(a) * radius + seed, Math.sin(a) * radius, seed * 3.1); }
// Camera shake with decay. Returns {x, y, r}.
export function shake(t, start, { amp = 30, freq = 22, decay = 7, rot = 0.03, seed = 1 } = {}) {
  if (t < start) return { x: 0, y: 0, r: 0 };
  const k = Math.exp(-(t - start) * decay), u = (t - start) * freq;
  return { x: noise1(u + seed) * amp * k, y: noise1(u + seed + 50) * amp * k, r: noise1(u + seed + 99) * rot * k };
}

// ───────────────────────── color ─────────────────────────
export function hex(h) { h = h.replace('#', ''); if (h.length === 3) h = [...h].map((c) => c + c).join(''); const n = parseInt(h, 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
export const rgba = (c, a = 1) => { const [r, g, b] = typeof c === 'string' ? hex(c) : c; return `rgba(${r | 0},${g | 0},${b | 0},${a})`; };
export const mixColor = (a, b, k) => rgba(mix(typeof a === 'string' ? hex(a) : a, typeof b === 'string' ? hex(b) : b, k));
// Curated palettes (60/30/10: bg, primary, accent, +support)
export const palettes = {
  electric: { bg: '#0B0B12', ink: '#F4F1EA', a: '#FF3D2E', b: '#2E5BFF', c: '#FFD23F' },
  acid: { bg: '#0E0E0E', ink: '#EDEDED', a: '#C6FF00', b: '#7A5CFF', c: '#FF4FD8' },
  paper: { bg: '#F2EDE4', ink: '#141414', a: '#FF5A1F', b: '#1F3BFF', c: '#00B37E' },
  midnight: { bg: '#05060F', ink: '#E8ECFF', a: '#6C7BFF', b: '#00E0C6', c: '#FF7AB6' },
  sunset: { bg: '#1A0B2E', ink: '#FFF4E6', a: '#FF6B35', b: '#F7C59F', c: '#EF476F' },
};

// ─────────────────────── 2D helpers ───────────────────────
export function rrect(ctx, x, y, w, h, r) { r = Math.min(r, w / 2, h / 2); ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
export function poly(ctx, pts, close = true) { ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); if (close) ctx.closePath(); }
// Apply a transform stack: translate → rotate → scale around an anchor.
export function xform(ctx, { x = 0, y = 0, r = 0, sx = 1, sy = sx, ax = 0, ay = 0 } = {}) { ctx.translate(x, y); ctx.rotate(r); ctx.scale(sx, sy); ctx.translate(-ax, -ay); }

// SVG path utilities (uses the browser's SVG geometry engine).
const _svg = typeof document !== 'undefined' ? document.createElementNS('http://www.w3.org/2000/svg', 'path') : null;
const _lenCache = new Map();
export function pathLength(d) { if (!_lenCache.has(d)) { _svg.setAttribute('d', d); _lenCache.set(d, _svg.getTotalLength()); } return _lenCache.get(d); }
// Trim Paths: draw only the portion [start,end] (0..1) of path d, shifted by offset (0..1, wraps).
export function trimPath(ctx, d, start, end, offset = 0) {
  const L = pathLength(d); let s = start + offset, e = end + offset; if (e - s <= 0.0005) return;
  const p = new Path2D(d);
  if (e - s >= 0.9995) { ctx.setLineDash([]); ctx.stroke(p); return; }
  s = fract(s); e = s + (end - start);
  ctx.setLineDash([(e - s) * L, L * 2]); ctx.lineDashOffset = -s * L; ctx.stroke(p);
  if (e > 1) { ctx.setLineDash([(e - 1) * L, L * 2]); ctx.lineDashOffset = 0; ctx.stroke(p); }
  ctx.setLineDash([]); ctx.lineDashOffset = 0;
}
// Resample a path into n evenly spaced points (for morphs, particles along paths, text-on-path).
export function samplePath(d, n) { _svg.setAttribute('d', d); const L = _svg.getTotalLength(); const out = []; for (let i = 0; i < n; i++) { const p = _svg.getPointAtLength((i / n) * L); out.push([p.x, p.y]); } return out; }
// Polygon helpers for morph targets
export const circlePts = (n, r, cx = 0, cy = 0, rot = -Math.PI / 2) => Array.from({ length: n }, (_, i) => [cx + Math.cos(rot + (i / n) * TAU) * r, cy + Math.sin(rot + (i / n) * TAU) * r]);
export function polygonPts(n, sides, r, rot = -Math.PI / 2) { const corners = circlePts(sides, r, 0, 0, rot); const out = []; for (let i = 0; i < n; i++) { const f = (i / n) * sides; const a = corners[Math.floor(f) % sides], b = corners[(Math.floor(f) + 1) % sides]; out.push(mix(a, b, f - Math.floor(f))); } return out; }
// Morph between equal-length point lists, rotating b to minimise travel (avoids "twisting").
export function alignPts(a, b) { let best = 0, bestD = Infinity; for (let s = 0; s < b.length; s++) { let d = 0; for (let i = 0; i < a.length; i += 4) { const q = b[(i + s) % b.length]; d += (a[i][0] - q[0]) ** 2 + (a[i][1] - q[1]) ** 2; } if (d < bestD) { bestD = d; best = s; } } return a.map((_, i) => b[(i + best) % b.length]); }
export const morphPts = (a, b, k) => a.map((p, i) => mix(p, b[i], k));

// Measure per-glyph positions for per-character animation (text animators).
export function glyphs(ctx, str, tracking = 0) {
  const out = []; let x = 0;
  for (const ch of str) { const w = ctx.measureText(ch).width; out.push({ ch, x, w }); x += w + tracking; }
  const width = x - tracking; out.forEach((g) => (g.cx = g.x + g.w / 2 - width / 2)); return { glyphs: out, width };
}

// Draw a list of drawables that each have a `z` for painter's-sort (2.5D).
export const byDepth = (items) => items.sort((a, b) => b.z - a.z);
// Simple perspective projection for 2.5D parallax/multiplane in pure 2D.
export function project(x, y, z, { fov = 900, cx = 0, cy = 0 } = {}) { const s = fov / (fov + z); return { x: cx + x * s, y: cy + y * s, s }; }
