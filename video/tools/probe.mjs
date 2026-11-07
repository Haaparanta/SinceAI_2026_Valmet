// Probe: can headed/headless Chrome render twinbuild.click with the GPU, and does Playwright record a 1920x1080 video?
import { chromium } from "playwright-core";
const headless = process.env.HEADLESS === "1";
const browser = await chromium.launch({
  channel: "chrome",
  headless,
  args: ["--window-size=1920,1080", "--window-position=0,0", "--ignore-gpu-blocklist", "--enable-gpu-rasterization"],
});
const ctx = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  recordVideo: { dir: "recordings/probe", size: { width: 1920, height: 1080 } },
});
const page = await ctx.newPage();
const t0 = Date.now();
await page.goto("https://twinbuild.click/?scene=manual");
await page.waitForFunction(() => document.body.dataset.loaded === "points", null, { timeout: 180000 });
console.log("loaded in", ((Date.now() - t0) / 1000).toFixed(1), "s");
const info = await page.evaluate(() => {
  const c = document.querySelector("canvas");
  const g = c.getContext("webgl2") || c.getContext("webgl");
  const d = g && g.getExtension("WEBGL_debug_renderer_info");
  return { renderer: d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : "n/a", dpr: devicePixelRatio, w: innerWidth, h: innerHeight };
});
console.log(info);
const fps = await page.evaluate(() => new Promise((r) => { let n = 0; const t0 = performance.now(); (function f() { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else r(n / 2); })(); }));
console.log("rAF fps idle", fps);
await page.mouse.move(960, 540);
await page.mouse.down();
const t1 = performance.now();
await page.mouse.move(1300, 480, { steps: 90 });
console.log("drag of 90 steps took", (performance.now() - t1).toFixed(0), "ms");
await page.mouse.up();
await page.waitForTimeout(800);
const v = page.video();
await ctx.close();
console.log("video", await v.path());
await browser.close();
