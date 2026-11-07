#!/usr/bin/env node
/** Copies every asset the storyboard names (repo-relative paths) into public/assets/, and recordings/*.mp4 into public/recordings/. */
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const repo = resolve(root, "..");
const story = JSON.parse(readFileSync(resolve(root, "storyboard.json"), "utf8"));
const wanted = new Set();
for (const s of story.scenes) for (const a of s.assets ?? []) if (!/^screen[- ]recording/i.test(a)) wanted.add(a);
for (const a of story.extra_assets ?? []) wanted.add(a);
let copied = 0;
const missing = [];
for (const a of wanted) {
  const src = resolve(repo, a);
  const dst = resolve(root, "public/assets", a);
  if (!existsSync(src)) { missing.push(a); continue; }
  mkdirSync(dirname(dst), { recursive: true });
  if (!existsSync(dst) || statSync(dst).size !== statSync(src).size) { copyFileSync(src, dst); copied++; }
}
const rec = resolve(root, "recordings");
if (existsSync(rec)) {
  mkdirSync(resolve(root, "public/recordings"), { recursive: true });
  for (const f of readdirSync(rec)) if (/\.mp4$/.test(f)) {
    const src = resolve(rec, f), dst = resolve(root, "public/recordings", f);
    if (!existsSync(dst) || statSync(dst).size !== statSync(src).size) { copyFileSync(src, dst); copied++; }
  }
}
console.log(`${wanted.size} assets wanted, ${copied} copied`);
if (missing.length) { console.error("missing:\n  " + missing.join("\n  ")); process.exit(1); }
