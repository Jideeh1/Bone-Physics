// TEMPLATE — 3D (three.js) scene with optional 2D overlay ('hybrid').
import * as mg from '/lib/mg.js';
const { seg, spring, lerp, TAU } = mg;

const W = 1920, H = 1080, D = 6;
let THREE, scene, camera, hero, key, rim, v3;

export default {
  title: 'Untitled 3D', width: W, height: H, fps: 30, duration: D, mode: 'hybrid',
  motionBlur: { samples: 4, shutter: 180 },
  finish: { grain: 0.05, vignette: 0.4, bloom: { strength: 0.4, radius: 30, threshold: 0.7 } },
  async setup({ THREE: T, renderer }) {
    THREE = T; v3 = new THREE.Vector3();
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    scene = new THREE.Scene(); scene.background = new THREE.Color('#0B0B12'); scene.fog = new THREE.Fog('#0B0B12', 10, 30);
    camera = new THREE.PerspectiveCamera(30, W / H, 0.1, 100);
    hero = new THREE.Mesh(new THREE.IcosahedronGeometry(1.2, 0), new THREE.MeshStandardMaterial({ color: '#FF3D2E', roughness: 0.35, flatShading: true }));
    hero.castShadow = true; scene.add(hero);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshStandardMaterial({ color: '#15151F', roughness: 0.9 }));
    floor.rotation.x = -Math.PI / 2; floor.position.y = -1.4; floor.receiveShadow = true; scene.add(floor);
    key = new THREE.DirectionalLight('#FFE2C4', 3); key.position.set(4, 8, 5); key.castShadow = true; key.shadow.mapSize.set(1024, 1024); scene.add(key);
    rim = new THREE.DirectionalLight('#6C7BFF', 3); rim.position.set(-6, 3, -6); scene.add(rim);
    scene.add(new THREE.HemisphereLight('#8FA0FF', '#0B0B12', 0.5));
  },
  render(t, { renderer, ctx }) {
    const ph = (t / D) * TAU; // seamless-loop phase
    camera.position.set(Math.cos(ph * 0.25) * 9, 3 + Math.sin(ph) * 0.3, Math.sin(ph * 0.25) * 9); camera.lookAt(0, 0, 0);
    hero.rotation.set(ph, ph * 2, 0);
    hero.scale.setScalar(spring(t - 0.2, { freq: 1.8, damping: 0.4 }));
    renderer.render(scene, camera);
    // 2D label pinned to the 3D object
    v3.set(0, 1.8, 0).project(camera);
    ctx.font = '700 36px "Inter Display", sans-serif'; ctx.textAlign = 'center'; ctx.fillStyle = '#F4F1EA';
    ctx.globalAlpha = seg(t, 0.8, 0.4); ctx.fillText('HERO', (v3.x + 1) / 2 * W, (1 - v3.y) / 2 * H); ctx.globalAlpha = 1;
  },
};
