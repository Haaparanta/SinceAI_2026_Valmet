/**
 * Browser tests for the web viewer (index.html) and the snapshot page (capture.html).
 *
 *   make test-web                                  # writes the viewer fixture if no export exists, then runs these
 *   node --test tests/web/                         # same, once data/derived/viewer/scene.{bin,json} exist
 *
 * Starts its own Vite dev server (port A2B_WEB_TEST_PORT, default 5199) and drives headless Chromium through the
 * playwright-core that web/ already depends on. Browser: $CHROME_PATH, else /opt/pw-browsers/chromium (cloud sessions),
 * else the installed Google Chrome. Expectations are read from data/derived/viewer/scene.json, so they hold for the
 * synthetic fixture (scripts/make_viewer_fixture.py) and for a real export alike.
 */
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { after, before, describe, test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const WEB = resolve(ROOT, "web");
const SCENE_JSON = resolve(ROOT, "data/derived/viewer/scene.json");
const AUTO_DIR = resolve(ROOT, "data/derived/viewer_auto");
const PORT = Number(process.env.A2B_WEB_TEST_PORT ?? 5199);
const BASE = `http://127.0.0.1:${PORT}`;
const { chromium } = createRequire(resolve(WEB, "package.json"))("playwright-core");

if (!existsSync(SCENE_JSON)) {
  throw new Error(`${SCENE_JSON} missing: run \`make test-web\` (writes the fixture) or \`make viewer\``);
}
const meta = JSON.parse(readFileSync(SCENE_JSON, "utf8"));
const parts = meta.parts;
const last = parts.at(-1);
const above = parts.find((p) => meta.dollhouse_cut_y != null && p.bbox.min[1] > meta.dollhouse_cut_y);
const below = parts.find((p) => meta.dollhouse_cut_y == null || p.bbox.max[1] < meta.dollhouse_cut_y);
const autoMeta = existsSync(resolve(AUTO_DIR, "scene.json")) ? JSON.parse(readFileSync(resolve(AUTO_DIR, "scene.json"), "utf8")) : null;

let vite;
let browser;
let stopping = false;

async function waitForServer(url, ms = 20000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`vite did not answer on ${url} within ${ms} ms`);
}

function launchOptions() {
  const path = process.env.CHROME_PATH ?? (existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : "");
  return path ? { executablePath: path } : { channel: "chrome" };
}

before(async () => {
  vite = spawn(process.execPath, [resolve(WEB, "node_modules/vite/bin/vite.js"), "--host", "127.0.0.1", "--port",
    String(PORT), "--strictPort"], { cwd: WEB, stdio: ["ignore", "pipe", "pipe"] });
  let log = "";
  vite.stdout.on("data", (d) => (log += d));
  vite.stderr.on("data", (d) => (log += d));
  vite.on("exit", (code) => code && !stopping && console.error(`vite exited ${code}:\n${log}`));
  await waitForServer(`${BASE}/`);
  browser = await chromium.launch(launchOptions());
});

after(async () => {
  await browser?.close();
  stopping = true;
  vite?.kill();
});

/** A fresh viewer page that has finished loading the scene; collects page errors and failed requests. */
async function openViewer(query = "") {
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const problems = [];
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  page.on("console", (m) => m.type() === "error" && !/Failed to load resource/.test(m.text()) && problems.push(m.text()));
  page.on("response", (r) => r.status() >= 400 && !r.url().endsWith("/favicon.ico") && problems.push(`${r.status()} ${r.url()}`));
  await page.goto(`${BASE}/${query}`);
  await page.waitForFunction(() => window.__a2b, null, { timeout: 20000 });
  return { page, problems };
}

const search = (page) => new URL(page.url()).searchParams;

/** Pixels that differ from the clear colour in the viewer's current frame. */
async function litPixels(page, { hideSelected = false } = {}) {
  return page.evaluate((hide) => {
    const { renderer, scene, camera, cloud } = window.__a2b;
    const sel = cloud.passes[2].points;
    const was = sel.visible;
    if (hide) sel.visible = false;
    renderer.render(scene, camera);
    sel.visible = was;
    const gl = renderer.getContext();
    const w = gl.drawingBufferWidth;
    const h = gl.drawingBufferHeight;
    const px = new Uint8Array(w * h * 4);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const hex = scene.background.getHex(); // sRGB, as written to the canvas (.r/.g/.b are linear)
    const [r0, g0, b0] = [(hex >> 16) & 255, (hex >> 8) & 255, hex & 255];
    let n = 0;
    for (let i = 0; i < px.length; i += 4) {
      if (Math.abs(px[i] - r0) + Math.abs(px[i + 1] - g0) + Math.abs(px[i + 2] - b0) > 24) n++;
    }
    return n;
  }, hideSelected);
}

describe("viewer (index.html)", () => {
  test("loads the scene: stats, part list, build label, synthetic badge, no errors", async () => {
    const { page, problems } = await openViewer();
    const stats = await page.textContent("#stats");
    assert.match(stats, new RegExp(`^${meta.count.toLocaleString("en-US")} points`));
    assert.match(stats, new RegExp(`in ${parts.length} accepted parts`));
    assert.equal(await page.locator("#parts li").count(), parts.length);
    assert.equal(await page.textContent("#upto-label"), `${parts.length} / ${parts.length} · ${last.label}`);
    assert.ok(await page.locator(".badge", { hasText: "SYNTHETIC DATA" }).isVisible(), "SYNTHETIC DATA badge (AGENTS.md §8)");
    assert.equal(search(page).get("src"), "overlay", "default source");
    const lit = await litPixels(page);
    assert.ok(lit > 1000 && lit < 0.9 * 1400 * 900, `the point cloud draws something (${lit} lit pixels)`);
    assert.deepEqual(problems, []);
    await page.close();
  });

  test("source buttons and keys 1-4 switch the source, exactly one pressed, URL follows", async () => {
    const { page, problems } = await openViewer();
    const sources = ["scan", "model", "overlay", "wireframe"];
    for (const [i, src] of sources.entries()) {
      for (const how of ["click", "key"]) {
        if (how === "click") await page.click(`#source button[data-source=${src}]`);
        else {
          await page.click(`#source button[data-source=${sources[(i + 1) % 4]}]`); // move away first
          await page.keyboard.press(String(i + 1));
        }
        const pressed = await page.$$eval("#source button[aria-pressed=true]", (bs) => bs.map((b) => b.dataset.source));
        assert.deepEqual(pressed, [src], `${how} ${src}`);
        assert.equal(search(page).get("src"), src);
      }
    }
    assert.deepEqual(problems, []);
    await page.close();
  });

  test("style toggle: red/grey sets style=redgrey, true colour removes it", async () => {
    const { page } = await openViewer();
    await page.click("#style button[data-style=redgrey]");
    assert.equal(search(page).get("style"), "redgrey");
    assert.equal(await page.getAttribute("#style button[data-style=redgrey]", "aria-pressed"), "true");
    await page.click("#style button[data-style=true]");
    assert.equal(search(page).get("style"), null);
    await page.close();
  });

  test("selecting a part highlights it, frames it and writes part=; clicking again or Esc clears", async () => {
    const { page } = await openViewer();
    const p = parts[Math.min(5, parts.length - 1)];
    const camBefore = await page.evaluate(() => window.__a2b.camera.position.toArray());
    await page.click(`#parts li[data-seq="${p.seq}"]`);
    assert.equal(search(page).get("part"), p.name);
    assert.deepEqual(await page.$$eval("#parts li.selected", (ls) => ls.map((l) => Number(l.dataset.seq))), [p.seq]);
    const camAfter = await page.evaluate(() => window.__a2b.camera.position.toArray());
    assert.notDeepEqual(camAfter, camBefore, "camera flies to the part");
    await page.click(`#parts li[data-seq="${p.seq}"]`);
    assert.equal(search(page).get("part"), null, "second click deselects");
    await page.click(`#parts li[data-seq="${p.seq}"]`);
    await page.keyboard.press("Escape");
    assert.equal(search(page).get("part"), null, "Esc deselects");
    assert.equal(await page.locator("#parts li.selected").count(), 0);
    await page.close();
  });

  test("build replay: arrows and slider move upto, later parts turn future, stats count only built parts", async () => {
    const { page } = await openViewer();
    await page.keyboard.press("ArrowLeft");
    await page.keyboard.press("ArrowLeft");
    const k = parts.length - 2;
    assert.equal(search(page).get("upto"), String(k));
    assert.equal(await page.textContent("#upto-label"), `${k} / ${parts.length} · ${parts[k - 1].label}`);
    assert.equal(await page.locator("#parts li.future").count(), 2);
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("ArrowRight"); // clamps at the end
    assert.equal(search(page).get("upto"), null, "upto is dropped from the URL when everything is built");

    await page.$eval("#upto", (el) => {
      el.value = "3";
      el.dispatchEvent(new Event("input"));
    });
    const built = parts.slice(0, 3).reduce((a, p) => a + p.count, 0);
    assert.match(await page.textContent("#stats"), new RegExp(`${built.toLocaleString("en-US")} in 3 accepted parts`));
    assert.equal(await page.locator("#parts li.future").count(), parts.length - 3);
    await page.$eval("#upto", (el) => {
      el.value = "0";
      el.dispatchEvent(new Event("input"));
    });
    assert.equal(await page.textContent("#upto-label"), `0 / ${parts.length}`);
    await page.close();
  });

  test("selecting a part after upto extends the build to it", async () => {
    const { page } = await openViewer("?upto=1");
    await page.click(`#parts li[data-seq="${last.seq}"]`);
    assert.equal(search(page).get("upto"), null);
    assert.equal(search(page).get("part"), last.name);
    await page.close();
  });

  test("boxes and cutaway toggles (buttons and B / D keys) flip aria-pressed", async () => {
    const { page } = await openViewer();
    await page.click("#boxes");
    assert.equal(await page.getAttribute("#boxes", "aria-pressed"), "true");
    assert.equal(search(page).get("boxes"), "1");
    await page.keyboard.press("b");
    assert.equal(await page.getAttribute("#boxes", "aria-pressed"), "false");
    await page.click("#cut");
    assert.equal(await page.getAttribute("#cut", "aria-pressed"), "true");
    await page.keyboard.press("d");
    assert.equal(await page.getAttribute("#cut", "aria-pressed"), "false");
    await page.close();
  });

  test("URL state is restored on load (shareable links)", async () => {
    const p = parts[Math.min(9, parts.length - 1)];
    const upto = Math.max(p.seq, parts.length - 3);
    const { page, problems } = await openViewer(`?src=wireframe&style=redgrey&part=${p.name}&upto=${upto}&boxes=1`);
    assert.equal(await page.getAttribute("#source button[data-source=wireframe]", "aria-pressed"), "true");
    assert.equal(await page.getAttribute("#style button[data-style=redgrey]", "aria-pressed"), "true");
    assert.equal(await page.getAttribute("#boxes", "aria-pressed"), "true");
    assert.equal(await page.locator(`#parts li.selected[data-seq="${p.seq}"]`).count(), 1);
    assert.equal(await page.locator("#parts li.future").count(), parts.length - upto);
    assert.deepEqual(problems, []);
    await page.close();
  });

  test("Snapshot button opens capture.html with the same state and camera, and it renders", async () => {
    const p = below ?? parts[0];
    const { page } = await openViewer(`?src=model&part=${p.name}`);
    const [popup] = await Promise.all([page.waitForEvent("popup"), page.click("#snap")]);
    const q = new URL(popup.url()).searchParams;
    assert.equal(new URL(popup.url()).pathname, "/capture.html");
    assert.equal(q.get("src"), "model");
    assert.equal(q.get("part"), p.name);
    assert.ok(q.get("cam") && q.get("look"), "camera is carried over");
    await popup.waitForSelector("body[data-ready='1']", { timeout: 20000 });
    assert.equal(await popup.getAttribute("body", "data-error"), null);
    const info = JSON.parse(await popup.getAttribute("body", "data-info"));
    assert.equal(info.selected, p.name);
    assert.deepEqual(info.size, [1400, 900]);
    await page.close();
  });

  test("missing export: the status line says how to make one", async () => {
    const page = await browser.newPage();
    await page.route("**/api/viewer/scene.json", (r) => r.fulfill({ status: 404, body: "missing" }));
    await page.goto(`${BASE}/`);
    await page.waitForFunction(() => /scene\.json -> 404/.test(document.querySelector("#stats").textContent));
    assert.match(await page.textContent("#stats"), /export_viewer_scene\.py/);
    await page.close();
  });

  test("scene.bin that does not match scene.json is reported, not drawn", async () => {
    const page = await browser.newPage();
    await page.route("**/api/viewer/scene.bin", (r) => r.fulfill({ status: 200, body: Buffer.alloc(18 * 10) }));
    await page.goto(`${BASE}/`);
    await page.waitForFunction(() => /re-export/.test(document.querySelector("#stats").textContent));
    await page.close();
  });

  test("a selected part below the dollhouse cut is drawn (control for the pixel measure below)", async (t) => {
    if (!below) return t.skip("no part lies below dollhouse_cut_y in this export");
    const { page } = await openViewer(`?src=model&part=${below.name}`);
    const added = (await litPixels(page)) - (await litPixels(page, { hideSelected: true }));
    assert.ok(added > 50, `${below.name}: selected pass adds ${added} lit pixels`);
    await page.close();
  });

  // regression: the auto-cutaway used to hide a selected part above the cut (lamps, pipes, ceiling); fixed in the shader
  test(
    "a selected part stays visible when the camera frames it from above the dollhouse cut",
    async (t) => {
      if (!above) return t.skip("no part lies above dollhouse_cut_y in this export");
      const { page } = await openViewer(`?src=model&part=${above.name}`);
      const withSel = await litPixels(page);
      const withoutSel = await litPixels(page, { hideSelected: true });
      assert.ok(withSel - withoutSel > 50, `${above.name}: selected pass adds ${withSel - withoutSel} lit pixels`);
      await page.close();
    },
  );
});

describe("snapshot page (capture.html)", () => {
  async function capture(query) {
    const page = await browser.newPage();
    await page.goto(`${BASE}/capture.html?${query}`);
    await page.waitForSelector("body[data-ready='1']", { timeout: 20000 });
    const error = await page.getAttribute("body", "data-error");
    const info = error ? null : JSON.parse(await page.getAttribute("body", "data-info"));
    return { page, error, info };
  }

  for (const view of ["top", "n", "s", "e", "w", "up"]) {
    test(`orthographic view=${view} renders with a size from the room bounds`, async () => {
      const { page, error, info } = await capture(`view=${view}&src=overlay`);
      assert.equal(error, null);
      assert.equal(info.camera.view, view);
      const [w, h] = info.size;
      assert.ok(w > 100 && h > 100, `size ${w}x${h}`);
      const canvas = await page.$eval("#scene", (c) => [c.width, c.height]);
      assert.deepEqual(canvas, [w, h]);
      await page.close();
    });
  }

  test("redgrey snapshot of a selected part: caption, badge colour, built list", async () => {
    const p = parts[Math.min(4, parts.length - 1)];
    const { page, error, info } = await capture(`part=${p.name}&style=redgrey&badge=ACCEPTED&title=Step%20${p.seq}`);
    assert.equal(error, null);
    assert.equal(info.selected, p.name);
    assert.deepEqual(info.built, parts.map((x) => x.name));
    assert.equal(await page.textContent("#caption .title"), `Step ${p.seq}`);
    assert.match(await page.textContent("#caption .legend"), /red = selected/);
    assert.equal(await page.$eval("#badge", (b) => getComputedStyle(b).backgroundColor), "rgb(46, 229, 157)");
    await page.close();
  });

  test("upto by name limits the built list", async () => {
    const { page, info } = await capture(`upto=${parts[2].name}`);
    assert.deepEqual(info.built, parts.slice(0, 3).map((x) => x.name));
    await page.close();
  });

  test("an unknown view is reported in data-error", async () => {
    const { page, error } = await capture("view=diagonal");
    assert.match(error, /view=diagonal: use one of/);
    await page.close();
  });
});

describe("both builds (?scene=both)", { skip: autoMeta ? false : "no data/derived/viewer_auto export: run `make viewer-fixture`" }, () => {
  const nManual = parts.length;
  const nAuto = autoMeta?.parts.length ?? 0;
  const autoPart = autoMeta?.parts.find((p) => p.kind !== "structure") ?? autoMeta?.parts[0];

  test("loads manual parts then automatic objects, tagged, coloured by origin, no errors", async () => {
    const { page, problems } = await openViewer("?scene=both");
    assert.equal(await page.locator("#parts li[data-seq]").count(), nManual + nAuto);
    assert.equal(await page.locator('#parts li[data-origin="manual"]').count(), nManual);
    assert.equal(await page.locator('#parts li[data-origin="auto"]').count(), nAuto);
    assert.equal(await page.textContent(`#parts li[data-seq="${nManual + 1}"] .origin-tag`), "AUTO");
    assert.match(await page.textContent("#stats"), new RegExp(`in ${nManual + nAuto} parts: ${nManual} manual \\+ ${nAuto} automatic`));
    assert.equal(await page.getAttribute('#build button[data-build="both"]', "aria-pressed"), "true");
    assert.equal(await page.getAttribute('#style button[data-style="origin"]', "aria-pressed"), "true", "both opens By origin");
    assert.equal(search(page).get("style"), null, "the default style stays out of the URL");
    assert.equal(search(page).get("scene"), "both");
    const lit = await litPixels(page);
    assert.ok(lit > 1000 && lit < 0.9 * 1400 * 900, `${lit} lit pixels`);
    assert.deepEqual(problems, []);
    await page.close();
  });

  test("the merged cloud is every manual row, then the automatic rows after its pool, part ids shifted", async () => {
    const { page } = await openViewer("?scene=both");
    const got = await page.evaluate(({ start, end }) => {
      const { cloud } = window.__a2b;
      const g = cloud.geometry;
      const pos = g.getAttribute("position").array;
      const part = g.getAttribute("part").array;
      return { count: part.length, xyz: Array.from(pos.slice(start * 3, start * 3 + 6)), ids: [part[start], part[end - 1]], meta: cloud.meta.parts.length };
    }, (() => {
      const shift = meta.count - autoMeta.pool_count;
      return { start: autoPart.start + shift, end: autoPart.end + shift };
    })());
    assert.equal(got.count, meta.count + autoMeta.count - autoMeta.pool_count);
    assert.equal(got.meta, nManual + nAuto);
    assert.deepEqual(got.ids, [autoPart.seq + nManual, autoPart.seq + nManual]);
    const bin = readFileSync(resolve(AUTO_DIR, "scene.bin"));
    const want = Array.from(new Float32Array(bin.buffer, bin.byteOffset + autoPart.start * 12, 6));
    assert.deepEqual(got.xyz, want, "positions come from the automatic export");
    await page.close();
  });

  test("origin chips filter the list; a manual part's card links to the overlapping automatic object", async () => {
    const { page } = await openViewer("?scene=both");
    await page.click('#kinds button[data-origin="auto"]');
    assert.equal(await page.locator("#parts li[data-seq]:not(.filtered)").count(), nAuto);
    assert.equal(await page.locator('#parts li[data-origin="manual"]:not(.filtered)').count(), 0);
    await page.click('#kinds button[data-origin="auto"]');
    assert.equal(await page.locator("#parts li[data-seq]:not(.filtered)").count(), nManual + nAuto, "second click: both again");
    // origin and kind combine (an origin click must not reset the kind)
    const kind = autoMeta.parts.find((p) => !parts.some((m) => m.kind === p.kind))?.kind ?? autoMeta.parts[0].kind;
    await page.click(`#kinds button[data-kind="${kind}"]`);
    await page.click('#kinds button[data-origin="auto"]');
    assert.equal(await page.getAttribute(`#kinds button[data-kind="${kind}"]`, "aria-pressed"), "true");
    assert.equal(await page.locator("#parts li[data-seq]:not(.filtered)").count(), autoMeta.parts.filter((p) => p.kind === kind).length);
    await page.click('#kinds button[data-origin="auto"]');
    await page.click('#kinds button[data-kind=""]');

    // the manual part with the best-overlapping automatic object, worked out here from the two scene.json files
    const iou = (a, b) => {
      let inter = 1;
      for (let k = 0; k < 3; k++) inter *= Math.max(0, Math.min(a.max[k], b.max[k]) - Math.max(a.min[k], b.min[k]));
      const vol = (x) => (x.max[0] - x.min[0]) * (x.max[1] - x.min[1]) * (x.max[2] - x.min[2]);
      return inter / (vol(a) + vol(b) - inter || 1);
    };
    let best = null;
    for (const m of parts.filter((p) => p.kind !== "structure")) {
      for (const a of autoMeta.parts) {
        const v = iou(m.bbox, a.bbox);
        if (!best || v > best.v) best = { m, a, v };
      }
    }
    await page.click(`#parts li[data-seq="${best.m.seq}"]`);
    assert.equal(await page.textContent("#card-origin"), "MANUAL");
    const link = page.locator("#card-facts button.link");
    if (best.v >= 0.1) {
      assert.match(await link.textContent(), new RegExp(`^auto: ${best.a.label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`));
      const nearNames = await page.$$eval("#card-near .n", (els) => els.map((e) => e.textContent));
      const manualLabels = new Set(parts.map((p) => p.label));
      assert.ok(nearNames.every((n) => manualLabels.has(n)), `nearest parts stay in the manual build: ${nearNames}`);
      await link.click();
      assert.equal(search(page).get("part"), best.a.name);
      assert.equal(await page.textContent("#card-origin"), "AUTO");
      assert.match(await page.textContent("#card-facts"), /Found by/);
    } else {
      assert.equal(await link.count(), 0);
    }
    await page.close();
  });

  test("the Build switch reloads into another build and keeps the view", async () => {
    const { page } = await openViewer("?scene=both&src=model");
    await Promise.all([page.waitForURL(/scene=auto/), page.click('#build button[data-build="auto"]')]);
    await page.waitForFunction(() => window.__a2b, null, { timeout: 20000 });
    assert.equal(search(page).get("src"), "model");
    assert.equal(await page.locator("#parts li[data-seq]").count(), nAuto);
    assert.equal(await page.locator("#parts .origin-tag").count(), 0, "a single build needs no origin tags");
    await Promise.all([page.waitForURL((u) => !u.searchParams.has("scene")), page.click('#build button[data-build="manual"]')]);
    await page.waitForFunction(() => window.__a2b, null, { timeout: 20000 });
    assert.equal(await page.locator("#parts li[data-seq]").count(), nManual);
    assert.equal(await page.getAttribute('#style button[data-style="true"]', "aria-pressed"), "true");
    assert.equal(await page.isVisible('#style button[data-style="origin"]'), false, "By origin is for both builds");
    await page.close();
  });

  test("Splats mode joins both splat files", async () => {
    const { page, problems } = await openViewer("?scene=both");
    await page.click('#render button[data-render="splats"]');
    await page.waitForFunction(() => window.__a2b.splats()?.ready || /Splats:/.test(document.querySelector("#toast").textContent), null, { timeout: 90000 });
    const total = meta.count + autoMeta.count - autoMeta.pool_count;
    assert.equal(await page.textContent("#toast"), `${total.toLocaleString("en-US")} Gaussian splats loaded`);
    assert.equal(search(page).get("render"), "splats");
    assert.deepEqual(problems, []);
    await page.close();
  });

  test("capture.html renders an automatic object from the combined scene, with the origin legend", async () => {
    const page = await browser.newPage();
    await page.goto(`${BASE}/capture.html?scene=both&part=${autoPart.name}&src=model`);
    await page.waitForSelector("body[data-ready='1']", { timeout: 30000 });
    assert.equal(await page.getAttribute("body", "data-error"), null);
    const info = JSON.parse(await page.getAttribute("body", "data-info"));
    assert.equal(info.selected, autoPart.name);
    assert.equal(info.state.style, "origin");
    assert.equal(info.built.length, nManual + nAuto);
    assert.match(await page.textContent("#caption .legend"), /cyan = manual build · amber = automatic build · red = selected/);
    await page.close();
  });
});
