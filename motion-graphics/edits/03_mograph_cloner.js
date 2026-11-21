// EDIT 03 — "Hex Field" · 3D MoGraph cloner · 1:1 · 8 s seamless loop
// Techniques: Cloner (instanced hex grid) + stacked effectors (radial ripple field, looping-noise
// field, step "selection" pop with spring), color ramp driven by effector strength, 60° camera
// orbit that exploits hex symmetry for a perfect loop, three-point lighting (warm key / cool rim /
// hemi fill), fog for aerial perspective, shadows, ACES tone-mapping, motion blur, bloom, grain.
import * as mg from '/lib/mg.js';
const { TAU, spring, clamp, lerp } = mg;

const W = 1080, H = 1080, D = 8; // loop period
const RINGS = 15, R = 0.5, GAP = 0.06;
let THREE, key, rim, scene, camera, mesh, cells = [], dummy, colA, colB, colC, tmpC;

export default {
  title: 'Hex Field',
  width: W, height: H, fps: 30, duration: D, mode: '3d',
  motionBlur: { samples: 4, shutter: 180 },
  finish: { grain: 0.06, vignette: 0.5, bloom: { strength: 0.55, radius: 40, threshold: 0.62 }, ca: 3 },
  audio: {
    bpm: 90, start: 0, kick: 'x.........x.....', hat: '....x.......x...', clap: '',
    pad: [['D3', 'F3', 'A3', 'C4'], ['A#2', 'D3', 'F3', 'A3'], ['F3', 'A3', 'C4', 'E4'], ['C3', 'E3', 'G3', 'B3']],
    events: [{ t: 2, type: 'shimmer' }, { t: 6, type: 'shimmer' }],
  },
  async setup(env) {
    THREE = env.THREE; const { renderer } = env;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMappingExposure = 1.1;
    scene = new THREE.Scene();
    const bg = new THREE.Color('#05060F'); scene.background = bg; scene.fog = new THREE.Fog(bg, 24, 44);
    camera = new THREE.PerspectiveCamera(28, W / H, 0.1, 100);

    // Cloner: axial hex grid
    for (let q = -RINGS; q <= RINGS; q++) for (let r = -RINGS; r <= RINGS; r++) {
      const s = -q - r; if (Math.max(Math.abs(q), Math.abs(r), Math.abs(s)) > RINGS) continue;
      const x = (R + GAP / 2) * Math.sqrt(3) * (q + r / 2), z = (R + GAP / 2) * 1.5 * r;
      const d = Math.hypot(x, z), a = Math.atan2(z, x);
      // selection hash is invariant under 60° rotation → 6-fold kaleidoscopic pops AND a seamless loop
      const am = ((a % (Math.PI / 3)) + Math.PI / 3) % (Math.PI / 3);
      cells.push({ x, z, d, a, sel: d < 0.1 ? 0 : mg.hash(Math.round(d * 40) * 0.37 + Math.round(am * 40) * 1.91) });
    }
    const geo = new THREE.CylinderGeometry(R, R, 1, 6); geo.translate(0, 0.5, 0); // pivot at base
    const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.35, roughness: 0.32 });
    mesh = new THREE.InstancedMesh(geo, mat, cells.length);
    mesh.castShadow = mesh.receiveShadow = true; scene.add(mesh);
    dummy = new THREE.Object3D();
    colA = new THREE.Color('#1B1F4A'); colB = new THREE.Color('#00E0C6'); colC = new THREE.Color('#FF7AB6'); tmpC = new THREE.Color();

    // Lighting: warm key with shadows, cool rim from behind, hemisphere fill
    key = new THREE.DirectionalLight('#FFE2C4', 3.2); key.position.set(6, 12, 4); key.castShadow = true;
    key.shadow.mapSize.set(1536, 1536); Object.assign(key.shadow.camera, { left: -14, right: 14, top: 14, bottom: -14, near: 1, far: 40 }); key.shadow.bias = -0.0008;
    scene.add(key);
    rim = new THREE.DirectionalLight('#6C7BFF', 4.0); rim.position.set(-8, 5, -10); scene.add(rim);
    scene.add(new THREE.HemisphereLight('#8FA0FF', '#05060F', 0.6));
  },
  render(t, { renderer }) {
    const ph = (t / D) * TAU; // loop phase
    // Camera: 60° orbit per loop (hex symmetry ⇒ seamless) + gentle bob
    const az = ph / 6 + 0.4, el = 0.78 + Math.sin(ph) * 0.04, dist = 31;
    camera.position.set(Math.cos(az) * Math.cos(el) * dist, Math.sin(el) * dist, Math.sin(az) * Math.cos(el) * dist);
    camera.lookAt(0, 0.6, 0);
    // Light rig travels with the camera (keeps lighting identical at the loop point)
    const rot = (x, z, k) => [x * Math.cos(k) - z * Math.sin(k), x * Math.sin(k) + z * Math.cos(k)];
    { const [x, z] = rot(6, 4, az - 0.4); key.position.set(x, 12, z); }
    { const [x, z] = rot(-8, -10, az - 0.4); rim.position.set(x, 5, z); }

    cells.forEach((c, i) => {
      // Effector 1: radial ripple field (2 waves per loop travelling outward)
      const ripple = Math.max(0, Math.sin(c.d * 0.75 - ph * 2)) ** 3;
      // Effector 2: looping 3D noise field
      // (sampled in camera-relative coords so the 60° orbit lands on an identical frame)
      const ca = Math.cos(-az), sa = Math.sin(-az), rx = c.x * ca - c.z * sa, rz = c.x * sa + c.z * ca;
      const n = (mg.noise3(rx * 0.16 + Math.cos(ph) * 1.2, rz * 0.16 + Math.sin(ph) * 1.2, 2.0) + 1) / 2;
      // Effector 3: step selection — ~6% of clones pop with a spring at staggered times in the loop
      let pop = 0;
      if (c.sel > 0.95) { const st = ((c.sel - 0.95) / 0.05) * D; const lt = ((t - st) % D + D) % D; pop = lt < D / 2 ? spring(lt, { freq: 1.6, damping: 0.35 }) * (1 - mg.seg(lt, D / 2 - 1, 1, 'inOutSine')) : 0; }
      // Falloff: stronger in the centre (spherical field)
      const fall = 1 - mg.smoothstep(4, 13, c.d);
      const strength = clamp(ripple * 0.9 * fall + n * 0.5 + pop * 1.0);
      const h = 0.15 + (ripple * 2.2 * fall + n * 1.1 + pop * 2.4) * lerp(0.35, 1, fall);
      dummy.position.set(c.x, 0, c.z);
      dummy.scale.set(lerp(0.82, 1, fall), h, lerp(0.82, 1, fall));
      dummy.rotation.set(0, pop * 0.35, 0);
      dummy.updateMatrix(); mesh.setMatrixAt(i, dummy.matrix);
      // Color ramp by effector strength (dark base → teal → pink at peaks)
      if (strength < 0.55) tmpC.copy(colA).lerp(colB, strength / 0.55); else tmpC.copy(colB).lerp(colC, (strength - 0.55) / 0.45);
      if (pop > 0.02) tmpC.lerp(new THREE.Color('#FFFFFF'), pop * 0.6);
      mesh.setColorAt(i, tmpC);
    });
    mesh.instanceMatrix.needsUpdate = true; mesh.instanceColor.needsUpdate = true;
    renderer.render(scene, camera);
  },
};
