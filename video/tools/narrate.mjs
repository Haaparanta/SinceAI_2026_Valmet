#!/usr/bin/env node
/**
 * Narration for the demo video: one audio clip per storyboard scene, with word timings for the captions.
 *
 *   node tools/narrate.mjs                      # ElevenLabs when ELEVENLABS_API_KEY is set (env or video/.env), else macOS `say`
 *   node tools/narrate.mjs --say                # force the macOS stand-in voice
 *   node tools/narrate.mjs --voice George       # ElevenLabs voice by name (premade) or voice_id
 *   node tools/narrate.mjs --model eleven_multilingual_v2 --force
 *   node tools/narrate.mjs --voices             # list the ElevenLabs premade voices and exit
 *
 * Reads  storyboard.json  (scenes[].id, scenes[].narration)
 * Writes public/narration/<scene>.mp3|wav and public/narration/manifest.json:
 *   { provider, voice, model, scenes: { <id>: { file, duration, text, words: [{ text, start, end }] } } }
 * Clips are cached by a hash of (provider, voice, model, text); --force regenerates everything.
 */
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const args = process.argv.slice(2);
const opt = { storyboard: resolve(root, "storyboard.json"), out: resolve(root, "public/narration"), voice: process.env.ELEVENLABS_VOICE ?? "George", model: process.env.ELEVENLABS_MODEL ?? "eleven_multilingual_v2", force: false, say: false, sayVoice: process.env.SAY_VOICE ?? "Samantha", listVoices: false, speed: Number(process.env.ELEVENLABS_SPEED ?? 1) };
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--storyboard") opt.storyboard = resolve(args[++i]);
  else if (a === "--out") opt.out = resolve(args[++i]);
  else if (a === "--voice") opt.voice = args[++i];
  else if (a === "--model") opt.model = args[++i];
  else if (a === "--speed") opt.speed = Number(args[++i]);
  else if (a === "--say-voice") opt.sayVoice = args[++i];
  else if (a === "--force") opt.force = true;
  else if (a === "--say") opt.say = true;
  else if (a === "--voices") opt.listVoices = true;
  else if (a === "-h" || a === "--help") { console.log(readFileSync(fileURLToPath(import.meta.url), "utf8").split("*/")[0]); process.exit(0); }
  else { console.error(`unknown argument ${a}`); process.exit(2); }
}

// video/.env (gitignored): KEY=VALUE lines
const envFile = resolve(root, ".env");
if (existsSync(envFile)) {
  for (const line of readFileSync(envFile, "utf8").split("\n")) {
    const m = /^\s*([A-Z0-9_]+)\s*=\s*"?([^"\n]*)"?\s*$/.exec(line);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
  }
}
const API_KEY = process.env.ELEVENLABS_API_KEY ?? process.env.XI_API_KEY;
const provider = opt.say || !API_KEY ? "say" : "elevenlabs";
const API = "https://api.elevenlabs.io";

async function xi(path, init = {}) {
  const res = await fetch(`${API}${path}`, { ...init, headers: { "xi-api-key": API_KEY, "Content-Type": "application/json", ...(init.headers ?? {}) } });
  if (!res.ok) throw new Error(`ElevenLabs ${init.method ?? "GET"} ${path}: ${res.status} ${await res.text()}`);
  return res.json();
}

async function listVoices() {
  const out = [];
  let token;
  do {
    const q = new URLSearchParams({ category: "premade", page_size: "100" });
    if (token) q.set("next_page_token", token);
    const data = await xi(`/v2/voices?${q}`);
    out.push(...data.voices);
    token = data.has_more ? data.next_page_token : undefined;
  } while (token);
  return out;
}

async function resolveVoice(nameOrId) {
  if (/^[A-Za-z0-9]{20}$/.test(nameOrId)) return { voice_id: nameOrId, name: nameOrId };
  const voices = await listVoices();
  const hit = voices.find((v) => v.name.toLowerCase() === nameOrId.toLowerCase()) ?? voices.find((v) => v.name.toLowerCase().startsWith(nameOrId.toLowerCase()));
  if (!hit) throw new Error(`no premade ElevenLabs voice called "${nameOrId}"; try --voices`);
  return hit;
}

/** characters + per-character times -> words with start/end */
function wordsFromAlignment(al) {
  const words = [];
  let cur = null;
  al.characters.forEach((ch, i) => {
    const s = al.character_start_times_seconds[i];
    const e = al.character_end_times_seconds[i];
    if (/\s/.test(ch)) { if (cur) { words.push(cur); cur = null; } return; }
    if (!cur) cur = { text: ch, start: s, end: e };
    else { cur.text += ch; cur.end = e; }
  });
  if (cur) words.push(cur);
  return words;
}

/** words timed in proportion to their length inside [start, end] (the `say` stand-in has no alignment) */
function spreadWords(text, start, end) {
  const toks = text.split(/\s+/).filter(Boolean);
  const weights = toks.map((t) => t.replace(/[^\p{L}\p{N}]/gu, "").length + 1.2 + (/[.,;:!?]$/.test(t) ? 1.5 : 0));
  const total = weights.reduce((a, b) => a + b, 0);
  let t = start;
  return toks.map((tok, i) => { const d = ((end - start) * weights[i]) / total; const w = { text: tok, start: t, end: t + d * 0.9 }; t += d; return w; });
}

function sentences(text) {
  return text.replace(/\s+/g, " ").trim().split(/(?<=[.!?])\s+(?=[A-Z0-9"“(])/).filter(Boolean);
}

/** read a 16-bit PCM WAV written by `say`: returns { rate, channels, pcm } */
function readWav(file) {
  const b = readFileSync(file);
  if (b.toString("ascii", 0, 4) !== "RIFF" || b.toString("ascii", 8, 12) !== "WAVE") throw new Error(`${file}: not a WAV`);
  let p = 12, rate = 0, channels = 0, bits = 0, pcm = null;
  while (p + 8 <= b.length) {
    const id = b.toString("ascii", p, p + 4);
    const size = b.readUInt32LE(p + 4);
    if (id === "fmt ") { channels = b.readUInt16LE(p + 10); rate = b.readUInt32LE(p + 12); bits = b.readUInt16LE(p + 22); }
    else if (id === "data") { pcm = b.subarray(p + 8, p + 8 + size); break; }
    p += 8 + size + (size & 1);
  }
  if (!pcm || bits !== 16) throw new Error(`${file}: expected 16-bit PCM`);
  return { rate, channels, pcm };
}
function writeWav(file, rate, channels, pcm) {
  const h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + pcm.length, 4); h.write("WAVE", 8); h.write("fmt ", 12); h.writeUInt32LE(16, 16);
  h.writeUInt16LE(1, 20); h.writeUInt16LE(channels, 22); h.writeUInt32LE(rate, 24); h.writeUInt32LE(rate * channels * 2, 28);
  h.writeUInt16LE(channels * 2, 32); h.writeUInt16LE(16, 34); h.write("data", 36); h.writeUInt32LE(pcm.length, 40);
  writeFileSync(file, Buffer.concat([h, pcm]));
}

/** macOS `say`, one call per sentence so every sentence has a measured start and end */
function synthSay(id, text) {
  const GAP = 0.3; // seconds between sentences
  const RATE = 22050;
  const parts = [];
  let pcmAll = [];
  let t = 0;
  const words = [];
  for (const s of sentences(text)) {
    const tmp = resolve(opt.out, `.${id}_tmp.wav`);
    execFileSync("say", ["-v", opt.sayVoice, "-r", "168", "-o", tmp, "--file-format=WAVE", `--data-format=LEI16@${RATE}`, s]);
    const w = readWav(tmp);
    unlinkSync(tmp);
    const dur = w.pcm.length / (2 * w.channels * w.rate);
    // trim trailing silence `say` leaves (under ~1 % amplitude for the last stretch)
    let endSample = w.pcm.length / 2;
    while (endSample > 0 && Math.abs(w.pcm.readInt16LE((endSample - 1) * 2)) < 200) endSample--;
    const spoken = Math.min(dur, endSample / w.rate + 0.12);
    words.push(...spreadWords(s, t, t + spoken));
    pcmAll.push(w.pcm.subarray(0, Math.min(w.pcm.length, Math.ceil(spoken * w.rate) * 2)));
    pcmAll.push(Buffer.alloc(Math.round(GAP * w.rate) * 2));
    t += spoken + GAP;
    parts.push({ s, spoken });
  }
  const pcm = Buffer.concat(pcmAll);
  const file = resolve(opt.out, `${id}.wav`);
  writeWav(file, RATE, 1, pcm);
  return { file: `narration/${id}.wav`, duration: pcm.length / (2 * RATE), words };
}

async function synthEleven(id, text, voice, prev, next) {
  const q = new URLSearchParams({ output_format: "mp3_44100_128" });
  const body = {
    text,
    model_id: opt.model,
    voice_settings: { stability: 0.5, similarity_boost: 0.8, style: 0.1, speed: opt.speed, use_speaker_boost: true },
    ...(prev ? { previous_text: prev } : {}),
    ...(next ? { next_text: next } : {}),
  };
  const data = await xi(`/v1/text-to-speech/${voice.voice_id}/with-timestamps?${q}`, { method: "POST", body: JSON.stringify(body) });
  const file = resolve(opt.out, `${id}.mp3`);
  writeFileSync(file, Buffer.from(data.audio_base64, "base64"));
  const al = data.alignment ?? data.normalized_alignment;
  const words = al ? wordsFromAlignment(al) : spreadWords(text, 0, 0);
  let duration = words.length ? words[words.length - 1].end : 0;
  try { // the file is a little longer than the last character; afinfo (macOS) knows exactly
    const m = /estimated duration: ([\d.]+) sec/.exec(execFileSync("afinfo", [file], { encoding: "utf8" }));
    if (m) duration = Math.max(duration, Number(m[1]));
  } catch { /* keep the alignment end */ }
  return { file: `narration/${id}.mp3`, duration, words };
}

const story = JSON.parse(readFileSync(opt.storyboard, "utf8"));
mkdirSync(opt.out, { recursive: true });
const manifestFile = resolve(opt.out, "manifest.json");
const old = existsSync(manifestFile) ? JSON.parse(readFileSync(manifestFile, "utf8")) : { scenes: {} };

if (opt.listVoices) {
  if (!API_KEY) { console.error("ELEVENLABS_API_KEY is not set"); process.exit(1); }
  for (const v of await listVoices()) console.log(`${v.voice_id}  ${v.name.padEnd(12)} ${Object.values(v.labels ?? {}).join(", ")}`);
  process.exit(0);
}

let voice = { voice_id: "say", name: opt.sayVoice };
if (provider === "elevenlabs") voice = await resolveVoice(opt.voice);
console.log(`narration: ${provider} · voice ${voice.name} · model ${provider === "elevenlabs" ? opt.model : "macOS say"}`);
if (provider === "say") console.log("  (stand-in voice: set ELEVENLABS_API_KEY in the environment or video/.env for the real narration)");

const scenes = story.scenes.filter((s) => (s.narration ?? "").trim());
const manifest = { provider, voice: voice.name, voice_id: voice.voice_id, model: provider === "elevenlabs" ? opt.model : "say", scenes: {} };
let generated = 0;
for (let i = 0; i < scenes.length; i++) {
  const s = scenes[i];
  const text = s.narration.replace(/\s+/g, " ").trim();
  const hash = createHash("sha1").update([provider, voice.voice_id, manifest.model, String(opt.speed), text].join("\0")).digest("hex").slice(0, 12);
  const cached = old.scenes?.[s.id];
  if (!opt.force && cached && cached.hash === hash && existsSync(resolve(opt.out, "..", cached.file))) {
    manifest.scenes[s.id] = cached;
    continue;
  }
  process.stdout.write(`  ${s.id} (${text.split(/\s+/).length} words) … `);
  const prev = scenes[i - 1]?.narration?.trim();
  const next = scenes[i + 1]?.narration?.trim();
  const r = provider === "elevenlabs" ? await synthEleven(s.id, text, voice, prev, next) : synthSay(s.id, text);
  manifest.scenes[s.id] = { ...r, text, hash };
  generated++;
  console.log(`${r.duration.toFixed(2)} s`);
}
writeFileSync(manifestFile, JSON.stringify(manifest, null, 2) + "\n");
const total = Object.values(manifest.scenes).reduce((a, s) => a + s.duration, 0);
console.log(`${generated} clip(s) generated, ${scenes.length} in the manifest, ${total.toFixed(1)} s of narration -> ${manifestFile}`);
