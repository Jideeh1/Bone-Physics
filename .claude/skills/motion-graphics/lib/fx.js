// fx.js — per-shot 2D post effects (operate on a source canvas, draw into ctx).
// Use inside scene.render() for transitions and stylised hits. The global finishing pass
// (grain/vignette/CA/bloom) lives in finish.js and runs automatically after every frame.
import { rng } from './mg.js';

const pool = new Map();
export function buffer(name, w, h) {
  const k = `${name}:${w}x${h}`;
  if (!pool.has(k)) { const c = document.createElement('canvas'); c.width = w; c.height = h; pool.set(k, c); }
  const c = pool.get(k); const x = c.getContext('2d');
  x.setTransform(1, 0, 0, 1, 0, 0); x.globalAlpha = 1; x.globalCompositeOperation = 'source-over'; x.filter = 'none';
  return c;
}

// Directional blur / smear (whip pans, speed lines). Averages n copies along (dx, dy).
export function smear(ctx, src, dx, dy, n = 16, x = 0, y = 0) {
  const len = Math.hypot(dx, dy);
  if (len < 1) { ctx.drawImage(src, x, y); return; }
  n = Math.max(2, Math.min(n, Math.ceil(len / 3)));
  const tmp = buffer('smear', src.width, src.height), tx = tmp.getContext('2d');
  tx.clearRect(0, 0, tmp.width, tmp.height);
  for (let i = 0; i < n; i++) { const k = i / (n - 1) - 0.5; tx.globalAlpha = 1 / (i + 1); tx.drawImage(src, dx * k, dy * k); }
  tx.globalAlpha = 1; ctx.drawImage(tmp, x, y);
}

// Isolate one channel (multiply by pure color) into a temp buffer.
function chan(name, src, color, dx, dy) {
  const c = buffer(name, src.width, src.height), x = c.getContext('2d');
  x.fillStyle = '#000'; x.fillRect(0, 0, c.width, c.height);
  x.drawImage(src, dx, dy); x.globalCompositeOperation = 'multiply'; x.fillStyle = color; x.fillRect(0, 0, c.width, c.height);
  return c;
}
// RGB split: R shifted one way, B the other, recombined additively.
export function rgbSplit(ctx, src, off, angle = 0) {
  const dx = Math.cos(angle) * off, dy = Math.sin(angle) * off;
  const r = chan('r', src, '#f00', dx, dy), g = chan('g', src, '#0f0', 0, 0), b = chan('b', src, '#00f', -dx, -dy);
  ctx.save(); ctx.fillStyle = '#000'; ctx.fillRect(0, 0, src.width, src.height);
  ctx.globalCompositeOperation = 'lighter'; ctx.drawImage(r, 0, 0); ctx.drawImage(g, 0, 0); ctx.drawImage(b, 0, 0); ctx.restore();
}

// Digital glitch: horizontal bands displaced + optional colour-band offset. `amount` 0..1.
export function glitch(ctx, src, amount, seed = 1) {
  const r = rng(seed), W = src.width, H = src.height;
  ctx.drawImage(src, 0, 0);
  const bands = Math.floor(6 + amount * 18);
  for (let i = 0; i < bands; i++) {
    const y = Math.floor(r() * H), h = Math.floor(4 + r() * 120 * amount), dx = (r() - 0.5) * W * 0.25 * amount;
    ctx.drawImage(src, 0, y, W, h, dx, y, W, h);
    if (r() < 0.25 * amount) { ctx.save(); ctx.globalCompositeOperation = 'difference'; ctx.fillStyle = r() < 0.5 ? '#ff00aa' : '#00ffee'; ctx.fillRect(0, y, W, h * 0.4); ctx.restore(); }
  }
}

// Radial zoom blur around (cx, cy): averages copies scaled by up to (1 + amount).
export function zoomBlur(ctx, src, cx, cy, amount, n = 14) {
  const tmp = buffer('zoom', src.width, src.height), tx = tmp.getContext('2d');
  tx.clearRect(0, 0, tmp.width, tmp.height);
  for (let i = 0; i < n; i++) { const s = 1 + (amount * i) / (n - 1); tx.globalAlpha = 1 / (i + 1); tx.setTransform(s, 0, 0, s, cx - cx * s, cy - cy * s); tx.drawImage(src, 0, 0); }
  tx.setTransform(1, 0, 0, 1, 0, 0); tx.globalAlpha = 1; ctx.drawImage(tmp, 0, 0);
}
