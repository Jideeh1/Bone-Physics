#!/usr/bin/env node
// render.js — frame-exact renderer for mg scenes → MP4 (+ synthesized, beat-synced audio).
//
//   node render.js <scene.js> <out.mp4> [options]
//     --still <sec> <out.png>   render one frame to PNG (fast look-dev)
//     --sheet                   also write <out>.sheet.png contact sheet (12 frames) for review
//     --every <n>               render every nth frame (draft preview, plays faster)
//     --from <sec> --to <sec>   render a sub-range
//     --no-audio                skip the audio track
//     --crf <n>                 x264 quality (default 17)
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn, spawnSync } = require('child_process');
const { chromium } = require('playwright');

const args = process.argv.slice(2);
if (args.length < 2) { console.error('usage: node render.js <scene.js> <out.mp4|out.png> [--still sec] [--sheet] [--every n] [--from s --to s] [--no-audio]'); process.exit(1); }
const scenePath = path.resolve(args[0]);
const outPath = path.resolve(args[1]);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : def; };
const flag = (name) => args.includes(name);
const LIB = path.join(__dirname, 'lib');
const SCENE_DIR = path.dirname(scenePath);

const TYPES = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.html': 'text/html', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.otf': 'font/otf' };
function serveFile(res, root, rel) {
  const p = path.normalize(path.join(root, rel));
  if (!p.startsWith(root) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end('nf'); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
}
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  if (u.startsWith('/lib/')) return serveFile(res, LIB, u.slice(5));
  if (u.startsWith('/scene/')) return serveFile(res, SCENE_DIR, u.slice(7));
  res.writeHead(404); res.end();
});

(async () => {
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--font-render-hinting=none'] });
  const page = await browser.newPage({ viewport: { width: 64, height: 64 } });
  page.on('console', (m) => { if ((m.type() === 'error' || m.type() === 'warning') && !m.text().includes('GL Driver Message')) console.error('[page]', m.text()); });
  page.on('pageerror', (e) => console.error('[page error]', e.message));
  await page.goto(`http://127.0.0.1:${port}/lib/harness.html?scene=/scene/${encodeURIComponent(path.basename(scenePath))}`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 120000 });
  const cfg = await page.evaluate(() => window.__config);
  await page.setViewportSize({ width: cfg.width, height: cfg.height });
  await page.evaluate(() => document.fonts.ready);
  const shot = async (f) => { await page.evaluate((fr) => window.__render(fr), f); return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: cfg.width, height: cfg.height } }); };

  // Still frame mode
  const still = opt('--still');
  if (still !== undefined) {
    const png = await shot(Math.round(parseFloat(still) * cfg.fps));
    fs.writeFileSync(outPath, png); console.log('wrote', outPath);
    await browser.close(); server.close(); return;
  }

  const every = parseInt(opt('--every', '1'), 10);
  const from = Math.round(parseFloat(opt('--from', '0')) * cfg.fps);
  const to = Math.round(parseFloat(opt('--to', String(cfg.duration))) * cfg.fps);
  const outFps = cfg.fps / every;
  const silent = outPath.replace(/\.mp4$/, '') + '.__video.mp4';
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(outFps), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', opt('--crf', '17'), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', silent], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now(); let count = 0;
  for (let f = from; f < to; f += every) {
    const buf = await shot(f);
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (++count % 30 === 0) console.log(`frame ${f}/${to} · ${((Date.now() - t0) / count).toFixed(0)} ms/frame`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  await browser.close(); server.close();

  // Audio: synthesize from the scene's `audio` spec and mux
  if (cfg.audio && !flag('--no-audio') && every === 1) {
    const spec = outPath + '.audio.json', wav = outPath + '.wav';
    fs.writeFileSync(spec, JSON.stringify({ ...cfg.audio, duration: cfg.duration, from: from / cfg.fps, to: to / cfg.fps }));
    const py = spawnSync('python3', ['-I', path.join(__dirname, 'audio.py'), spec, wav], { stdio: 'inherit' });
    if (py.status === 0) {
      spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', outPath], { stdio: 'inherit' });
      fs.unlinkSync(silent);
    } else fs.renameSync(silent, outPath);
    for (const f of [spec, wav]) if (fs.existsSync(f)) fs.unlinkSync(f);
  } else fs.renameSync(silent, outPath);
  console.log(`wrote ${outPath} (${count} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s)`);

  if (flag('--sheet')) {
    const sheet = outPath.replace(/\.mp4$/, '') + '.sheet.png';
    const dur = (to - from) / cfg.fps;
    const tw = cfg.width >= cfg.height ? 480 : 270;
    spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', outPath, '-vf', `fps=12/${dur},scale=${tw}:-2,tile=6x2:padding=4:color=white`, '-frames:v', '1', sheet], { stdio: 'inherit' });
    console.log('wrote', sheet);
  }
})().catch((e) => { console.error(e); process.exit(1); });
