// EDIT 05 — "Hype Edit" · 2D/3D hybrid velocity edit · 9:16 · 128 BPM · 8 s
// Techniques: every cut on the grid (beat = 0.46875 s), zoom-punch + decaying shake on kicks,
// chrome 3D hero (PMREM studio env reflections), whip-pan transition with directional smear,
// 2D shape burst with gravity/drag + per-letter sine wave, glitch/RGB-split transition with flash
// frame, 3D hex tunnel with a speed ramp (time remap: slow → 6x), zoom-through transition with
// radial blur, end card with beat pump. Hybrid: 3D is rendered, then drawn into the 2D comp so
// transitions/post apply to both.
import * as mg from '/lib/mg.js';
import * as fx from '/lib/fx.js';
const { seg, spring, lerp, clamp, TAU } = mg;

const W = 1080, H = 1920, BPM = 128, B = 60 / BPM;
const P = { bg: '#0A0A0F', ink: '#F5F3EE', a: '#C6FF00', b: '#7A5CFF', c: '#FF4FD8', d: '#00E5FF' };
const FONT = (w, px) => `${w} ${px}px "Inter Display", "Inter", sans-serif`;
const T1 = 4 * B, T2 = 8 * B, T3 = 12 * B; // section boundaries: 1.875, 3.75, 5.625 s
let THREE, R3, knotScene, knotCam, knot, tunScene, tunCam, rings, dummy, F1, F2;

// Speed ramp for the tunnel: speed(τ) in units/s, integrated deterministically → distance.
const speed = (u) => lerp(5, 60, seg(u, 1.0, 0.7, 'inExpo'));
function travel(tau) { let d = 0; const n = 90, h = tau / n; for (let i = 0; i < n; i++) d += speed((i + 0.5) * h) * h; return d; }

function kicker(ctx, txt, y, t, st, col = P.a) {
  ctx.font = FONT(600, 30); ctx.letterSpacing = '10px'; ctx.textAlign = 'center'; ctx.fillStyle = col;
  ctx.globalAlpha = seg(t, st, 0.15) ; ctx.fillText(txt, W / 2, y); ctx.globalAlpha = 1; ctx.letterSpacing = '0px';
}
function slamWord(ctx, word, x, y, size, t, st, col = P.ink, weight = 900) {
  if (t < st) return;
  const s = lerp(1.9, 1, spring(t - st, { freq: 3.2, damping: 0.42 }));
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.font = FONT(weight, size); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = col; ctx.fillText(word, 0, 0); ctx.restore();
}

// ── Sections: each draws a full frame into a 2D canvas `c` ──
function s1(c, t) { // chrome knot
  const x = c.getContext('2d');
  knot.rotation.set(t * 0.9, t * 1.3, 0);
  knotCam.position.z = lerp(11, 7.8, seg(t, 0, T1, 'outCubic'));
  R3.render(knotScene, knotCam); x.drawImage(R3.domElement, 0, 0);
  slamWord(x, 'BREAK', W / 2, 520, 210, t, 0.0);
  slamWord(x, 'THE', W / 2, 1360, 120, t, B * 1, P.a, 300);
  slamWord(x, 'FRAME', W / 2, 1520, 210, t, B * 2);
  kicker(x, 'VOL. 05 — MOTION', 1760, t, B * 3);
}
const SHAPES = Array.from({ length: 70 }, (_, i) => { const r = mg.rng(i + 5); return { a: r() * TAU, v: 600 + r() * 1500, s: 14 + r() * 40, k: Math.floor(r() * 3), spin: (r() - 0.5) * 14, col: [P.a, P.b, P.c, P.d][Math.floor(r() * 4)], beat: Math.floor(r() * 4) }; });
function s2(c, t) { // 2D burst + wave type
  const x = c.getContext('2d'); const lt = t - T1;
  x.fillStyle = '#121019'; x.fillRect(0, 0, W, H);
  // concentric beat rings
  for (let k = 0; k < 4; k++) { const bt = lt - k * B; if (bt < 0) continue; const e = seg(bt, 0, 0.6, 'outExpo'); x.strokeStyle = mg.rgba(P.b, 1 - e); x.lineWidth = 30 * (1 - e) + 2; x.beginPath(); x.arc(W / 2, H / 2, 80 + e * 900, 0, TAU); x.stroke(); }
  // particle burst: ballistic with drag & gravity, fired on each beat
  SHAPES.forEach((p) => {
    const bt = lt - p.beat * B; if (bt < 0) return;
    const drag = 3.2, d = (p.v / drag) * (1 - Math.exp(-drag * bt));
    const px = W / 2 + Math.cos(p.a) * d, py = H / 2 + Math.sin(p.a) * d + 900 * bt * bt * 0.5;
    const sc = Math.min(1, bt * 8) * (1 - seg(bt, 0.9, 0.6));
    if (sc <= 0) return;
    x.save(); x.translate(px, py); x.rotate(p.spin * bt); x.scale(sc, sc); x.fillStyle = p.col;
    if (p.k === 0) { x.beginPath(); x.arc(0, 0, p.s, 0, TAU); x.fill(); }
    else if (p.k === 1) { mg.poly(x, mg.circlePts(3, p.s * 1.3)); x.fill(); }
    else x.fillRect(-p.s, -p.s, p.s * 2, p.s * 2);
    x.restore();
  });
  // "MAKE IT MOVE" — MOVE letters ride a staggered sine wave
  x.textAlign = 'center'; x.textBaseline = 'alphabetic';
  slamWord(x, 'MAKE IT', W / 2, 760, 120, t, T1 + 0.05, P.a, 800);
  x.font = FONT(900, 300); const { glyphs } = mg.glyphs(x, 'MOVE', -6);
  glyphs.forEach((g, i) => {
    const appear = spring(lt - 0.1 - i * 0.06, { freq: 2.6, damping: 0.45 });
    const wave = Math.sin(lt * 9 - i * 0.9) * 40 * seg(lt, 0.5, 0.4);
    x.save(); x.translate(W / 2 + g.cx, 1080 + wave + (1 - appear) * 400); x.rotate(Math.sin(lt * 9 - i * 0.9) * 0.06);
    x.fillStyle = P.ink; x.globalAlpha = clamp(appear * 2); x.fillText(g.ch, 0, 0); x.restore();
  });
  x.globalAlpha = 1;
}
function s3(c, t) { // 3D hex tunnel with speed ramp
  const x = c.getContext('2d'); const lt = Math.max(0, t - T2);
  const dist = travel(lt), L = 120, N = rings.count;
  for (let i = 0; i < N; i++) {
    const z = -(((i * (L / N) - dist) % L) + L) % L;
    dummy.position.set(Math.sin(z * 0.05 + lt) * 0.6, Math.cos(z * 0.04) * 0.4, z);
    dummy.rotation.set(0, 0, i * 0.12 + lt * 0.8); dummy.scale.setScalar(1); dummy.updateMatrix(); rings.setMatrixAt(i, dummy.matrix);
  }
  rings.instanceMatrix.needsUpdate = true;
  tunCam.fov = lerp(55, 80, seg(lt, 1.0, 0.8, 'inExpo')); tunCam.updateProjectionMatrix();
  R3.render(tunScene, tunCam); x.drawImage(R3.domElement, 0, 0);
  const fast = seg(lt, 1.0, 0.5);
  x.save(); x.translate(W / 2, H / 2); x.transform(1, 0, -0.18 * fast, 1, 0, 0);
  x.font = FONT(900, 190); x.textAlign = 'center'; x.textBaseline = 'middle'; x.letterSpacing = `${lerp(0, 40, fast)}px`;
  x.fillStyle = P.ink; x.fillText(lt < 1.0 ? 'SLOW' : 'FAST', 0, 0); x.letterSpacing = '0px'; x.restore();
  kicker(x, lt < 1.0 ? 'DOWN' : 'FORWARD', 1100, t, T2 + 0.1, P.c);
}
function s4(c, t) { // end card
  const x = c.getContext('2d'); const lt = t - T3;
  x.fillStyle = P.a; x.fillRect(0, 0, W, H);
  const pump = mg.beatPulse(t, BPM, 10, T3);
  x.save(); x.translate(W / 2, H / 2); x.scale(1 + pump * 0.03, 1 + pump * 0.03);
  x.font = FONT(900, 280); x.textAlign = 'center'; x.textBaseline = 'alphabetic'; x.fillStyle = P.bg;
  const { glyphs } = mg.glyphs(x, 'MOVE.', -10);
  x.beginPath(); x.rect(-W / 2, -330, W, 380); x.clip();
  glyphs.forEach((g, i) => x.fillText(g.ch, g.cx, 40 + (1 - seg(lt, 0.05 + i * 0.04, 0.5, 'snap')) * 380));
  x.restore();
  x.font = FONT(600, 34); x.letterSpacing = '12px'; x.textAlign = 'center'; x.fillStyle = P.bg; x.globalAlpha = seg(lt, 0.6, 0.4);
  x.fillText('MADE WITH CODE', W / 2, H / 2 + 150); x.globalAlpha = 1; x.letterSpacing = '0px';
  x.strokeStyle = P.bg; x.lineWidth = 8; mg.trimPath(x, `M ${W / 2 - 200} ${H / 2 + 200} L ${W / 2 + 200} ${H / 2 + 200}`, 0, seg(lt, 0.8, 0.6, 'snap'));
}

export default {
  title: 'Hype Edit',
  width: W, height: H, fps: 30, duration: 8, mode: 'hybrid',
  motionBlur: { samples: 5, shutter: 180 },
  finish: { grain: 0.08, vignette: 0.4, ca: 4, bloom: { strength: 0.35, radius: 30, threshold: 0.7 } },
  audio: {
    bpm: BPM, start: 0, kick: 'x...x...x...x...', clap: '....x.......x...', hat: 'x.xxx.xxx.xxx.xx',
    bass: 'x..x..x.x..x..x.', bassNotes: ['F1', 'F1', 'G#1', 'A#1'], musicTo: 7.6,
    events: [{ t: T1, type: 'whoosh', dur: 0.35 }, { t: T2, type: 'glitch' }, { t: T2 + B * 2, type: 'riser', dur: B * 2 }, { t: T2 + 1.0, type: 'whoosh', dur: 0.4 },
      { t: T3, type: 'impact' }, { t: T3 + 0.9, type: 'shimmer' }],
  },
  async setup(env) {
    THREE = env.THREE; R3 = env.renderer; R3.toneMappingExposure = 1.15;
    F1 = fx.buffer('F1', W, H); F2 = fx.buffer('F2', W, H);
    // Studio environment for chrome reflections (built procedurally, then PMREM-filtered)
    const envScene = new THREE.Scene();
    const sky = new THREE.Mesh(new THREE.SphereGeometry(40, 32, 16), new THREE.MeshBasicMaterial({ side: THREE.BackSide, color: '#0b0b14' }));
    envScene.add(sky);
    const panel = (col, pos, w, h, inten) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(col).multiplyScalar(inten), side: THREE.DoubleSide })); m.position.set(...pos); m.lookAt(0, 0, 0); envScene.add(m); };
    panel('#ffffff', [0, 12, 4], 20, 3, 3); panel(P.c, [-14, 2, 0], 4, 24, 2.5); panel(P.d, [14, -2, 2], 4, 24, 2.5); panel(P.a, [0, -12, -6], 24, 3, 1.5); panel('#ffffff', [6, 4, 14], 6, 6, 2);
    const envTex = new THREE.PMREMGenerator(R3).fromScene(envScene, 0.03).texture;
    knotScene = new THREE.Scene(); knotScene.background = new THREE.Color(P.bg); knotScene.environment = envTex;
    knot = new THREE.Mesh(new THREE.TorusKnotGeometry(1.25, 0.42, 320, 48, 2, 3), new THREE.MeshStandardMaterial({ color: '#ffffff', metalness: 1, roughness: 0.1 }));
    knotScene.add(knot);
    knotCam = new THREE.PerspectiveCamera(40, W / H, 0.1, 100);
    // Tunnel: hexagonal rings (TorusGeometry with 6 tubular segments), coloured by index
    tunScene = new THREE.Scene(); tunScene.background = new THREE.Color('#05030A'); tunScene.fog = new THREE.Fog('#05030A', 20, 110);
    const N = 70; rings = new THREE.InstancedMesh(new THREE.TorusGeometry(3.2, 0.07, 6, 6), new THREE.MeshBasicMaterial({ color: '#ffffff' }), N);
    const cols = [P.c, P.b, P.d, P.a].map((c) => new THREE.Color(c));
    for (let i = 0; i < N; i++) rings.setColorAt(i, cols[i % 4]);
    tunScene.add(rings); dummy = new THREE.Object3D();
    tunCam = new THREE.PerspectiveCamera(55, W / H, 0.1, 200); tunCam.position.set(0, 0, 4);
  },
  render(t, { ctx }) {
    // Pick section(s) + transition
    const whip = seg(t, T1 - 0.12, 0.24, 'whip');           // 0→1 across T1
    const zoomT = seg(t, T3 - 0.3, 0.3, 'inExpo');          // zoom-through into T3
    let src;
    if (t < T1 - 0.12) { s1(F1, t); src = F1; }
    else if (t < T1 + 0.12) {                                // WHIP PAN: both shots slide, smear by velocity
      s1(F1, t); s2(F2, t);
      const off = whip * W, v = mg.vel((u) => seg(u, T1 - 0.12, 0.24, 'whip') * W, t) / 30;
      const comp = fx.buffer('whip', W, H), cx = comp.getContext('2d');
      cx.fillStyle = '#000'; cx.fillRect(0, 0, W, H); cx.drawImage(F1, -off, 0); cx.drawImage(F2, W - off, 0);
      fx.smear(ctx, comp, -v * 1.2, 0, 24); return;
    }
    else if (t < T2) { s2(F1, t); src = F1; }
    else if (t < T3 - 0.3) { s3(F1, t); src = F1; }
    else if (t < T3) {                                       // ZOOM-THROUGH with radial blur
      s3(F1, t); fx.zoomBlur(ctx, F1, W / 2, H / 2, zoomT * 1.5);
      ctx.fillStyle = mg.rgba(P.a, zoomT); ctx.fillRect(0, 0, W, H); return;
    }
    else { s4(F1, t); src = F1; }

    // Zoom punch + shake on each kick (sections 1–3), stronger after the speed ramp
    const kickAmt = t < T3 ? 1 : 0.4;
    const bt = ((t % B) + B) % B; const punch = Math.exp(-bt * 12) * kickAmt;
    const sh = mg.shake(t, Math.floor(t / B) * B, { amp: 22 * kickAmt, freq: 26, decay: 9, rot: 0.012, seed: Math.floor(t / B) });
    const s = 1 + punch * 0.06;
    const tmp = fx.buffer('punch', W, H), tx = tmp.getContext('2d');
    tx.fillStyle = '#000'; tx.fillRect(0, 0, W, H);
    tx.translate(W / 2 + sh.x, H / 2 + sh.y); tx.rotate(sh.r); tx.scale(s, s); tx.drawImage(src, -W / 2, -H / 2); tx.setTransform(1, 0, 0, 1, 0, 0);
    // GLITCH transition into section 3 (4 frames) + RGB split on the fast part of the tunnel
    if (t >= T2 - 0.07 && t < T2 + 0.07) { fx.glitch(ctx, tmp, 1, Math.floor(t * 30)); fx.rgbSplit(ctx, ctx.canvas, 18); }
    else if (t >= T2 + 1.0 && t < T3) fx.rgbSplit(ctx, tmp, 3 + punch * 16, Math.PI / 2);
    else ctx.drawImage(tmp, 0, 0);
    if (t >= T3 && t < T3 + 2 / 30) { ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.fillRect(0, 0, W, H); } // flash frame
    ctx.fillStyle = `rgba(0,0,0,${seg(t, 7.6, 0.4)})`; ctx.fillRect(0, 0, W, H);
  },
};
