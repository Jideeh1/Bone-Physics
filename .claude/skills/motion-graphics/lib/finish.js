// finish.js — the "finishing pass" every pro piece gets after animation:
// bloom → chromatic aberration → vignette → grain (grain always LAST).
import { rng } from './mg.js';

const mk = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
let T = null; // temp canvases, lazily sized
function temps(w, h) {
  if (T && T.w === w && T.h === h) return T;
  const grainTiles = [];
  const r = rng(99);
  for (let k = 0; k < 6; k++) {
    const g = mk(384, 384), gx = g.getContext('2d'), id = gx.createImageData(384, 384);
    for (let i = 0; i < id.data.length; i += 4) { const v = 128 + (r() + r() + r() - 1.5) * 120; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; }
    gx.putImageData(id, 0, 0); grainTiles.push(g);
  }
  T = { w, h, a: mk(w, h), r: mk(w, h), g: mk(w, h), b: mk(w, h), small: mk(Math.ceil(w / 4), Math.ceil(h / 4)), small2: mk(Math.ceil(w / 4), Math.ceil(h / 4)), grainTiles };
  return T;
}

function channel(dst, src, color, scale, w, h) {
  const x = dst.getContext('2d');
  // Opaque black first: multiply over transparent margins would otherwise leave pure-color edges.
  x.globalCompositeOperation = 'source-over'; x.fillStyle = '#000'; x.fillRect(0, 0, w, h);
  x.save(); x.translate(w / 2, h / 2); x.scale(scale, scale); x.drawImage(src, -w / 2, -h / 2); x.restore();
  x.globalCompositeOperation = 'multiply'; x.fillStyle = color; x.fillRect(0, 0, w, h);
  x.globalCompositeOperation = 'source-over';
}

// src: canvas with the averaged (motion-blurred) frame. out: visible canvas.
export function finish(src, out, opts = {}, frame = 0) {
  const w = out.width, h = out.height, o = out.getContext('2d');
  const t = temps(w, h);
  o.globalCompositeOperation = 'source-over'; o.globalAlpha = 1; o.filter = 'none';

  // 1. Chromatic aberration (lateral: grows toward the frame edges, like a real lens)
  if (opts.ca) {
    const k = opts.ca / Math.max(w, h);
    channel(t.r, src, '#ff0000', 1 + k, w, h);
    channel(t.g, src, '#00ff00', 1, w, h);
    channel(t.b, src, '#0000ff', 1 - k, w, h);
    o.fillStyle = '#000'; o.fillRect(0, 0, w, h);
    o.globalCompositeOperation = 'lighter';
    o.drawImage(t.r, 0, 0); o.drawImage(t.g, 0, 0); o.drawImage(t.b, 0, 0);
    o.globalCompositeOperation = 'source-over';
  } else {
    o.drawImage(src, 0, 0);
  }

  // 2. Bloom: threshold → downsample → blur (two radii) → screen back on top
  if (opts.bloom) {
    const { strength = 0.6, radius = 30, threshold = 0.65 } = opts.bloom;
    const k = 4, x = (0.5 - 0.5 / k) / threshold;
    const s = t.small, sx = s.getContext('2d');
    sx.filter = `brightness(${x}) contrast(${k})`; sx.clearRect(0, 0, s.width, s.height); sx.drawImage(out, 0, 0, s.width, s.height); sx.filter = 'none';
    const s2 = t.small2.getContext('2d');
    o.globalCompositeOperation = 'screen';
    for (const [rad, a] of [[radius / 4, strength], [radius, strength * 0.8]]) {
      s2.clearRect(0, 0, s.width, s.height); s2.filter = `blur(${rad / 4}px)`; s2.drawImage(s, 0, 0); s2.filter = 'none';
      o.globalAlpha = a; o.drawImage(t.small2, 0, 0, w, h);
    }
    o.globalAlpha = 1; o.globalCompositeOperation = 'source-over';
  }

  // 3. Vignette (off-center allowed via opts.vignetteCenter = [0..1, 0..1])
  if (opts.vignette) {
    const [cx, cy] = opts.vignetteCenter || [0.5, 0.5];
    const R = Math.hypot(w, h) / 2;
    const g = o.createRadialGradient(cx * w, cy * h, R * 0.35, cx * w, cy * h, R * 1.05);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${opts.vignette})`);
    o.fillStyle = g; o.fillRect(0, 0, w, h);
  }

  // 4. Animated grain — always last so nothing softens it
  if (opts.grain) {
    const tile = t.grainTiles[frame % t.grainTiles.length];
    const r = rng(frame * 7 + 3); const ox = Math.floor(r() * 384), oy = Math.floor(r() * 384);
    o.globalCompositeOperation = 'overlay'; o.globalAlpha = opts.grain;
    for (let y = -oy; y < h; y += 384) for (let x = -ox; x < w; x += 384) o.drawImage(tile, x, y);
    o.globalAlpha = 1; o.globalCompositeOperation = 'source-over';
  }
}
