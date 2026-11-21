// TEMPLATE — 2D scene. Copy next to your project, rename, then:
//   node .claude/skills/motion-graphics/render.js my_scene.js out.mp4 --sheet
import * as mg from '/lib/mg.js';
const { seg, spring, lerp, beat } = mg;

const W = 1080, H = 1920, BPM = 120, B = (n) => beat(BPM, n);
const P = mg.palettes.electric;
const FONT = (w, px) => `${w} ${px}px "Inter Display", "Inter", sans-serif`;

// Beat sheet — write this first.
const SHOT = { intro: 0, hit: B(4), outro: B(12) };

export default {
  title: 'Untitled', width: W, height: H, fps: 30, duration: 8,
  motionBlur: { samples: 8, shutter: 180 },
  finish: { grain: 0.06, vignette: 0.35, ca: 3 },
  audio: { bpm: BPM, kick: 'x...x...x...x...', hat: '..x...x...x...x.', clap: '....x.......x...', musicTo: 7.6,
    events: [{ t: SHOT.hit, type: 'whoosh', dur: 0.4 }, { t: SHOT.hit, type: 'impact' }] },
  render(t, { ctx, frameTime }) {
    ctx.fillStyle = P.bg; ctx.fillRect(0, 0, W, H);
    // Hero: spring scale-in on the hit
    const s = lerp(0, 1, spring(t - SHOT.hit, { freq: 2.4, damping: 0.45 }));
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(s, s);
    ctx.font = FONT(900, 220); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = P.ink;
    ctx.fillText('HELLO', 0, 0); ctx.restore();
    // Secondary: underline draws on after the hero lands
    ctx.strokeStyle = P.a; ctx.lineWidth = 10; ctx.lineCap = 'round';
    mg.trimPath(ctx, `M ${W / 2 - 260} ${H / 2 + 140} L ${W / 2 + 260} ${H / 2 + 140}`, 0, seg(t, SHOT.hit + 0.25, 0.6, 'snap'));
    // Outro
    ctx.fillStyle = mg.rgba('#000', seg(t, SHOT.outro + 1.4, 0.5)); ctx.fillRect(0, 0, W, H);
  },
};
