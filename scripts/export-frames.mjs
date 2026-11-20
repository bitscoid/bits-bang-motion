/* =========================================================
   Render opener jadi urutan PNG, frame demi frame.

   Bukan rekaman layar: skrip ini MENYETEL waktu timeline, menunggu
   browser selesai menggambar, baru menangkap. Jadi tidak ada frame
   yang drop walau satu frame butuh 300 ms untuk dirender.

   Prasyarat:
     npm i puppeteer
     python -m http.server 5178      (di folder proyek, jendela lain)

   Pakai (landscape, default):
     node scripts/export-frames.mjs
     ffmpeg -framerate 60 -i frames/f%05d.png -c:v libx264 -pix_fmt yuv420p -crf 16 opener.mp4

   Pakai (portrait 9:16, dengan audio):
     WIDTH=1080 HEIGHT=1920 FPS=60 node scripts/export-frames.mjs
     ffmpeg -framerate 60 -i frames/f%05d.png -i audio/voiceover.wav \
       -c:v libx264 -pix_fmt yuv420p -crf 16 -c:a aac -b:a 192k -shortest out.mp4

   WIDTH/HEIGHT harus sama dengan panggung di index.html (?ratio=9x16).
   Tanpa itu, potret menangkap sudut kiri-atas panggung 1920x1080.
   ========================================================= */

import puppeteer from 'puppeteer';
import { mkdir } from 'node:fs/promises';

const URL   = process.env.URL   || 'http://127.0.0.1:5178/index.html?clean=1';
const FPS   = Number(process.env.FPS   || 60);
const OUT   = process.env.OUT   || 'frames';
const WIDTH = Number(process.env.WIDTH  || 1920);
const HEIGHT= Number(process.env.HEIGHT || 1080);
const SCALE = Number(process.env.SCALE || 1);   // 1 = ukuran penuh, 0.5 = separuh

await mkdir(OUT, { recursive: true });

const browser = await puppeteer.launch({
  headless: 'new',
  // --no-sandbox: Chrome refuses to start as root without it. Harmless elsewhere.
  args: ['--enable-gpu', '--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist',
         '--no-sandbox', '--disable-setuid-sandbox', '--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage();
await page.setViewport({ width: WIDTH, height: HEIGHT, deviceScaleFactor: SCALE });
await page.goto(URL, { waitUntil: 'networkidle0' });

// tunggu sampai modul selesai dimuat dan timeline terpasang
await page.waitForFunction('window.OPENER && window.OPENER.ready && (!window.OPENER.clipsReady || window.OPENER.clipsReady())', { timeout: 120000 });
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => { window.OPENER.tl.pause(0); });

const DURATION = await page.evaluate(() => window.OPENER.DURATION);
const total = Math.ceil(DURATION * FPS);
console.log(`${total} frame @ ${FPS} fps (${DURATION}s) ${WIDTH}x${HEIGHT} -> ${OUT}/`);

for(let i = 0; i < total; i++){
  const t = i / FPS;

  // setel waktu, lalu biarkan DUA rAF lewat: satu untuk GSAP menulis gaya,
  // satu lagi untuk loop render menggambar frame dengan nilai baru itu.
  await page.evaluate(async (time) => {
    if (window.OPENER.seekFrame) await window.OPENER.seekFrame(time);   // ada klip video: tunggu frame-nya siap
    else (window.OPENER.seek||window.OPENER.tl.time.bind(window.OPENER.tl))(time);
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  }, t);

  await page.screenshot({
    path: `${OUT}/f${String(i).padStart(5, '0')}.png`,
    clip: { x: 0, y: 0, width: WIDTH, height: HEIGHT },
    optimizeForSpeed: true,
  });

  if(i % FPS === 0) process.stdout.write(`\r${i}/${total}  ${t.toFixed(1)}s`);
}

console.log(`\nselesai — ${total} frame di ${OUT}/`);
await browser.close();
