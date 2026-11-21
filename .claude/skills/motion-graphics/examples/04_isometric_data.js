// EDIT 04 — "Isometric Data Story" · hybrid 3D + 2D · 16:9 · 8 s
// Techniques: true isometric (orthographic camera, 35.264° tilt, 45° yaw), staggered spring bars
// (overshoot = "physical" data), data-to-data transition staggered from the centre, 2D labels
// tracking 3D anchors via projection (hybrid comp), eased number counters (never springs — numbers
// must not overshoot), ortho "dolly" via zoom, camera swing for parallax on the transition,
// shadow-catcher ground, soft clean lighting, title mask rise, outro fall with accelerate ease.
import * as mg from '/lib/mg.js';
const { seg, spring, lerp, clamp } = mg;

const W = 1920, H = 1080;
const C = { bg: '#E9ECF5', ink: '#151826', mute: '#6B7186', a: '#2E5BFF', b: '#FF5A1F', slab: '#FFFFFF' };
const A = [32, 48, 41, 66, 58, 84], B = [44, 36, 62, 57, 90, 118];
const LABELS = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6'];
const FONT = (w, px) => `${w} ${px}px "Inter Display", "Inter", sans-serif`;
let THREE, scene, cam, bars = [], tops = [], key, v3;

const hOf = (v) => v / 24; // data → world units
function barValue(i, t) {
  // spring in (staggered), spring to dataset B (staggered from centre), accelerate out
  const inK = spring(t - 0.9 - i * 0.09, { freq: 1.5, damping: 0.42 });
  const toB = spring(t - 4.3 - mg.stagger(i, 6, 0.08, 'center'), { freq: 1.6, damping: 0.4 });
  const out = seg(t, 7.1 + i * 0.04, 0.45, 'accel');
  return lerp(A[i], B[i], toB) * inK * (1 - out);
}
function shownValue(i, t) { // eased (non-overshooting) for numbers
  const inK = seg(t - i * 0.09, 0.9, 1.0, 'outExpo');
  const toB = seg(t - mg.stagger(i, 6, 0.08, 'center'), 4.3, 1.1, 'outExpo');
  return lerp(A[i], B[i], toB) * inK;
}

export default {
  title: 'Isometric Data Story',
  width: W, height: H, fps: 30, duration: 8, mode: 'hybrid',
  motionBlur: { samples: 4, shutter: 180 },
  finish: { grain: 0.04, vignette: 0.12 },
  audio: {
    bpm: 100, start: 0.9, kick: 'x.......x.......', hat: '..x...x...x...x.', clap: '....x.......x...',
    bass: 'x.....x...x.....', bassNotes: ['C2', 'C2', 'A1', 'G1'], musicTo: 7.6,
    events: [{ t: 0.85, type: 'whoosh', dur: 0.5 }, ...[0, 1, 2, 3, 4, 5].map((i) => ({ t: 0.95 + i * 0.09, type: 'pop', gain: 0.6 })),
      { t: 4.3, type: 'whoosh', dur: 0.6 }, { t: 4.35, type: 'sub' }, { t: 5.4, type: 'shimmer' }, { t: 7.1, type: 'whoosh', dur: 0.5 }],
  },
  async setup(env) {
    THREE = env.THREE; const { renderer } = env;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.NoToneMapping; // flat graphic look: keep brand colors exact
    scene = new THREE.Scene(); scene.background = new THREE.Color(C.bg);
    const asp = W / H, f = 6.2;
    cam = new THREE.OrthographicCamera(-f * asp, f * asp, f, -f, -100, 100);
    v3 = new THREE.Vector3();
    // Shadow catcher ground + slab
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.ShadowMaterial({ opacity: 0.12 }));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.4; ground.receiveShadow = true; scene.add(ground);
    const slab = new THREE.Mesh(new THREE.BoxGeometry(11, 0.4, 4.2), new THREE.MeshStandardMaterial({ color: C.slab, roughness: 0.9 }));
    slab.position.y = -0.2; slab.receiveShadow = slab.castShadow = true; scene.add(slab);
    for (let k = 0; k < 7; k++) { // grid lines on the slab
      const ln = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.01, 4.0), new THREE.MeshBasicMaterial({ color: '#D5D9E6' }));
      ln.position.set(-4.5 + k * 1.5, 0.006, 0); scene.add(ln);
    }
    const geo = new THREE.BoxGeometry(0.9, 1, 0.9); geo.translate(0, 0.5, 0);
    for (let i = 0; i < 6; i++) {
      const col = new THREE.Color(C.a).lerp(new THREE.Color('#8FA6FF'), 1 - i / 5);
      const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: col, roughness: 0.55 }));
      m.position.set(-3.75 + i * 1.5, 0, 0); m.castShadow = m.receiveShadow = true; scene.add(m); bars.push(m);
    }
    key = new THREE.DirectionalLight('#FFFFFF', 2.0); key.position.set(-5, 12, 7); key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048); Object.assign(key.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 0.1, far: 50 }); key.shadow.radius = 4; key.shadow.bias = -0.0005;
    scene.add(key); scene.add(new THREE.HemisphereLight('#FFFFFF', '#C9CEE0', 1.5));
    const fill = new THREE.DirectionalLight('#FFE7D6', 0.6); fill.position.set(8, 3, -4); scene.add(fill);
  },
  render(t, { renderer, ctx, frameTime }) {
    const ft = frameTime ?? t; // numbers are evaluated at the frame centre → no blur ghosting
    // Camera: isometric base, swing on the data change, ortho zoom "dolly"
    const yaw = mg.deg(45) + mg.deg(-14) * seg(t, 3.9, 1.6, 'smooth') + mg.deg(-4) * seg(t, 0, 8, 'linear');
    const tilt = Math.atan(1 / Math.SQRT2);
    const r = 30; cam.position.set(Math.sin(yaw) * Math.cos(tilt) * r, Math.sin(tilt) * r, Math.cos(yaw) * Math.cos(tilt) * r);
    cam.lookAt(0.9, 1.1, 0.3);
    cam.zoom = lerp(0.9, 1.22, seg(t, 0, 1.6, 'decel')) * lerp(1, 1.06, seg(t, 4.0, 3.5, 'inOutSine'));
    cam.updateProjectionMatrix();
    let maxI = 0;
    bars.forEach((m, i) => {
      const v = barValue(i, t); m.scale.y = Math.max(0.001, hOf(v)); m.visible = v > 0.05;
      if (B[i] > B[maxI]) maxI = i;
    });
    // Accent the winner after the transition (color pulls toward orange)
    const acc = seg(t, 5.0, 0.6);
    bars[maxI].material.color.set(C.a).lerp(new THREE.Color(C.b), acc);
    renderer.render(scene, cam);

    // ── 2D overlay (hybrid): labels pinned to 3D anchors ──
    const proj = (x, y, z) => { v3.set(x, y, z).project(cam); return [(v3.x + 1) / 2 * W, (1 - v3.y) / 2 * H]; };
    ctx.textAlign = 'center';
    bars.forEach((m, i) => {
      const v = barValue(i, t); if (v < 1) return;
      const [x, y] = proj(m.position.x, hOf(v) + 0.25, m.position.z);
      const a = seg(t, 1.3 + i * 0.09, 0.3) * (1 - seg(t, 7.0, 0.3));
      ctx.globalAlpha = a; ctx.fillStyle = i === maxI && acc > 0.5 ? C.b : C.ink;
      ctx.font = FONT(800, 34); ctx.fillText(Math.round(shownValue(i, ft)), x, y - 10);
      const [lx, ly] = proj(m.position.x, -0.4, 2.6);
      ctx.fillStyle = C.mute; ctx.font = FONT(600, 22); ctx.fillText(LABELS[i], lx, ly + 10);
    });
    ctx.globalAlpha = 1;
    // Title block (mask rise), top-left, inside title-safe
    const title = (txt, y, size, w, col, st) => {
      ctx.save(); ctx.beginPath(); ctx.rect(120, y - size, 1000, size * 1.25); ctx.clip();
      ctx.font = FONT(w, size); ctx.textAlign = 'left'; ctx.fillStyle = col;
      const k = seg(t, st, 0.8, 'snap') - seg(t, 7.0, 0.5, 'accel');
      ctx.fillText(txt, 120, y + (1 - k) * size * 1.2); ctx.restore();
    };
    title('REVENUE, INDEXED', 150, 26, 700, C.a, 0.3);
    title(t < 4.3 ? 'Steady climb.' : 'Then a breakout.', 225, 72, 800, C.ink, t < 4.3 ? 0.4 : 4.4);
    // KPI counter, bottom-right: rolls with outExpo, swaps on the transition
    const kpi = lerp(0, 162, seg(ft, 1.0, 2.2, 'outExpo')) + lerp(0, 107, seg(ft, 4.4, 1.4, 'outExpo'));
    const ka = seg(t, 1.0, 0.4) * (1 - seg(t, 7.0, 0.4));
    ctx.globalAlpha = ka; ctx.textAlign = 'right'; ctx.fillStyle = C.ink; ctx.font = FONT(900, 120);
    ctx.fillText(`+${Math.round(kpi)}%`, W - 120, 245);
    ctx.font = FONT(600, 24); ctx.fillStyle = C.mute; ctx.letterSpacing = '4px'; ctx.fillText('INDEX GROWTH SINCE Q1', W - 120, 290); ctx.letterSpacing = '0px';
    ctx.globalAlpha = 1;
    ctx.fillStyle = mg.rgba(C.bg, seg(t, 7.55, 0.45)); ctx.fillRect(0, 0, W, H);
  },
};
