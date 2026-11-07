#!/usr/bin/env node
/**
 * Render capture.html views to numbered PNGs with headless Chrome (playwright-core + the installed Google Chrome;
 * nothing is downloaded). The scripted half of the 3D Model Anything cap.sh, without agent-browser.
 *
 *   cd web && npm run dev                      # in another terminal (or any server that serves capture.html)
 *   node tools/snap.mjs "src=overlay&part=pipe_3" "view=top&src=model" "part=pipe_3&style=redgrey&badge=ACCEPTED"
 *
 * Each query becomes images/<NNNN>_<YYYYMMDD-HHMMSS>.png (local time): NNNN continues from the highest index already
 * in the output folder, the same rule as pipeline/stepbuild/state.py, so these images interleave with the pipeline's.
 *
 *   --out <dir>      output folder (default: ../images, the repo's image record)
 *   --file <path>    write exactly this file (one query only)
 *   --url <origin>   default http://127.0.0.1:5173 (env SNAP_URL)
 *   --suffix <tag>   append _<tag> to the file name (allowed by the image-name rule)
 * Exit code 1 if a page reports an error (body[data-error]) or never becomes ready.
 */
import { mkdirSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const here = dirname(fileURLToPath(import.meta.url));
const IMAGE_RE = /^(\d{4,})_(\d{8}-\d{6})(?:_[\w-]+)?\.png$/;

const args = process.argv.slice(2);
const opt = { out: resolve(here, "../../images"), url: process.env.SNAP_URL ?? "http://127.0.0.1:5173" };
const queries = [];
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--out") opt.out = resolve(args[++i]);
  else if (a === "--file") opt.file = resolve(args[++i]);
  else if (a === "--url") opt.url = args[++i];
  else if (a === "--suffix") opt.suffix = args[++i];
  else if (a === "-h" || a === "--help") {
    console.log("usage: node tools/snap.mjs [--out dir | --file path.png] [--url origin] [--suffix tag] <query>...");
    process.exit(0);
  } else queries.push(a.replace(/^\?/, ""));
}
if (!queries.length) {
  console.error("give at least one capture.html query, e.g. \"src=overlay&part=pipe_3\"");
  process.exit(2);
}
if (opt.file && queries.length > 1) {
  console.error("--file takes exactly one query");
  process.exit(2);
}

const stamp = (d) => {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
};
function nextIndex(dir) {
  let max = 0;
  for (const name of readdirSync(dir)) {
    const m = IMAGE_RE.exec(name);
    if (m) max = Math.max(max, Number(m[1]));
  }
  return max + 1;
}

const browser = await chromium.launch({
  channel: process.env.CHROME_PATH ? undefined : "chrome",
  executablePath: process.env.CHROME_PATH,
  headless: true,
});
let failed = 0;
try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 1100 } });
  page.on("console", (m) => {
    if (m.type() === "error") console.error(`  [page] ${m.text()}`);
  });
  if (!opt.file) mkdirSync(opt.out, { recursive: true });
  let index = opt.file ? 0 : nextIndex(opt.out);
  for (const q of queries) {
    const url = `${opt.url.replace(/\/$/, "")}/capture.html?${q}`;
    await page.goto(url, { waitUntil: "load" });
    await page.waitForFunction(() => document.body.dataset.ready === "1", null, { timeout: 120_000 });
    const { error, info } = await page.evaluate(() => ({ error: document.body.dataset.error, info: document.body.dataset.info }));
    if (error) {
      console.error(`FAIL ${q}: ${error}`);
      failed++;
      continue;
    }
    const wrap = page.locator("#wrap");
    const box = await wrap.boundingBox();
    // fit the viewport to the canvas so WebGL pixels outside it are not lost (as cap.sh does)
    await page.setViewportSize({ width: Math.ceil(box.width) + 40, height: Math.ceil(box.height) + 40 });
    const file = opt.file ?? resolve(opt.out, `${String(index++).padStart(4, "0")}_${stamp(new Date())}${opt.suffix ? `_${opt.suffix}` : ""}.png`);
    mkdirSync(dirname(file), { recursive: true });
    await wrap.screenshot({ path: file });
    const { size, built, selected } = JSON.parse(info);
    console.log(`${file}  ${size.join("x")}  ${built.length} parts${selected ? `, selected ${selected}` : ""}`);
  }
} finally {
  await browser.close();
}
process.exit(failed ? 1 : 0);
