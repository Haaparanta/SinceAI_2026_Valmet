#!/usr/bin/env node
/** Writes out/a2b_demo.srt (and .vtt) from the narration word timings laid on the composition timeline, same pages as the burned-in captions. */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const story = JSON.parse(readFileSync(resolve(root, "storyboard.json"), "utf8"));
const manifest = JSON.parse(readFileSync(resolve(root, "public/narration/manifest.json"), "utf8"));
const FPS = 30, TAIL = 0.7, LEAD = 0.3;
function pages(words) {
  const out = []; let cur = [], len = 0;
  const flush = () => { if (cur.length) { out.push({ start: cur[0].start, end: cur[cur.length - 1].end, words: cur }); cur = []; len = 0; } };
  words.forEach((w, i) => { const prev = words[i - 1]; const gap = prev ? w.start - prev.end : 0; const ends = prev ? /[.!?]$/.test(prev.text) : false;
    if (cur.length && (len + w.text.length + 1 > 84 || gap > 0.7 || (ends && len > 36))) flush(); cur.push(w); len += w.text.length + 1; });
  flush();
  for (let i = 0; i < out.length; i++) { const n = out[i + 1]; out[i].end = Math.min(n ? n.start - 0.04 : out[i].end + 1.2, out[i].end + 1.2); }
  return out;
}
const ts = (s, sep) => { const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60; return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(Math.floor(x)).padStart(2, "0")}${sep}${String(Math.round((x % 1) * 1000)).padStart(3, "0")}`; };
let from = 0, n = 0, srt = "", vtt = "WEBVTT\n\n";
for (const s of story.scenes) {
  const clip = manifest.scenes[s.id];
  const lead = s.props?.lead ?? LEAD, tail = s.props?.tail ?? TAIL;
  const sec = Math.max(s.duration_s, clip ? clip.duration + lead + tail : 0);
  const frames = Math.round(sec * FPS);
  if (clip) for (const p of pages(clip.words)) {
    const sceneEnd = (from + frames) / FPS - 0.05; // a caption never runs into the next scene
    const a = from / FPS + lead + p.start, b = Math.min(from / FPS + lead + p.end, sceneEnd);
    const text = p.words.map((w) => w.text).join(" ");
    srt += `${++n}\n${ts(a, ",")} --> ${ts(b, ",")}\n${text}\n\n`;
    vtt += `${ts(a, ".")} --> ${ts(b, ".")}\n${text}\n\n`;
  }
  from += frames;
}
mkdirSync(resolve(root, "out"), { recursive: true });
writeFileSync(resolve(root, "out/a2b_demo.srt"), srt);
writeFileSync(resolve(root, "out/a2b_demo.vtt"), vtt);
console.log(`${n} captions, ${(from / FPS).toFixed(1)} s -> out/a2b_demo.srt, out/a2b_demo.vtt`);
