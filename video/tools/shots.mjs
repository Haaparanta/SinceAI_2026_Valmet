// Screenshots of the live viewer in a few states, 1920x1080, to plan the recording (headless Chrome).
import { chromium } from "playwright-core";
const BASE = process.env.SNAP_URL ?? "https://twinbuild.click";
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--ignore-gpu-blocklist"] });
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
async function open(q) {
  await page.goto(`${BASE}/${q}`);
  await page.waitForFunction(() => document.body.dataset.loaded === "points", null, { timeout: 180000 });
  await page.waitForTimeout(600);
}
await open("?scene=manual");
await page.screenshot({ path: "recordings/shots/manual_scan.png" });
// the part card: click "Pump 2" in the list
const li = page.locator("#parts li", { hasText: "Pump 2" }).first();
await li.click();
await page.waitForTimeout(900);
await page.screenshot({ path: "recordings/shots/manual_pump2_card.png" });
const box = await page.locator("#card").boundingBox();
const panel = await page.locator("#panel").boundingBox();
const hud = await page.locator("#hud").boundingBox();
const liBox = await li.boundingBox();
console.log(JSON.stringify({ card: box, panel, hud, pump2_li: liBox }));
await page.keyboard.press("Escape");
await open("?scene=auto&boxes=1&src=wireframe");
await page.screenshot({ path: "recordings/shots/auto_boxes.png" });
await open("?scene=both&style=origin");
await page.screenshot({ path: "recordings/shots/both_origin.png" });
const cmp = await page.locator("#compare").boundingBox();
console.log(JSON.stringify({ compare: cmp, summary: await page.locator("#compare-summary").textContent() }));
await open("?scene=manual&dollhouse=1");
await page.screenshot({ path: "recordings/shots/manual_cut.png" });
await browser.close();
