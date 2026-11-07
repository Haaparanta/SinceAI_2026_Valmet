import "./style.css";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer } from "three/addons/renderers/CSS2DRenderer.js";
import { MeasureView, pickPoint } from "./measure";
import { fmtGap, neighbours, ProximityView } from "./proximity";
import type { SplatLayer } from "./splats"; // the module (and Spark, ~1 MB gzipped) loads on first use
import {
  BuildCloud,
  buildFromUrl,
  frameBox,
  loadScene,
  METRES_PER_UNIT_GUESS,
  partBox,
  pickPart,
  readState,
  roomBox,
  SOURCES,
  writeState,
  type SceneMeta,
  type Source,
  type ViewState,
} from "./scene";
import { vrSupported, XrWalk } from "./xr";

const fmt = (n: number): string => n.toLocaleString("en-US");
const FOV = 50;

const canvas = document.querySelector<HTMLCanvasElement>("#scene")!;
const statsEl = document.querySelector<HTMLElement>("#stats")!;
const partsEl = document.querySelector<HTMLOListElement>("#parts")!;
const uptoEl = document.querySelector<HTMLInputElement>("#upto")!;
const uptoLabel = document.querySelector<HTMLElement>("#upto-label")!;
const cutBtn = document.querySelector<HTMLButtonElement>("#cut")!;
const boxesBtn = document.querySelector<HTMLButtonElement>("#boxes")!;
const snapBtn = document.querySelector<HTMLButtonElement>("#snap")!;
const homeBtn = document.querySelector<HTMLButtonElement>("#home")!;
const vrBtn = document.querySelector<HTMLButtonElement>("#vr")!;
const vrLabel = document.querySelector<HTMLElement>("#vr-label")!;
const panelEl = document.querySelector<HTMLElement>("#panel")!;
const panelToggle = document.querySelector<HTMLButtonElement>("#panel-toggle")!;
const loadingEl = document.querySelector<HTMLElement>("#loading")!;
const loadingText = document.querySelector<HTMLElement>("#loading-text")!;
const toastEl = document.querySelector<HTMLElement>("#toast")!;
const tipEl = document.querySelector<HTMLElement>("#tip")!;
const nearBtn = document.querySelector<HTMLButtonElement>("#near")!;
const measureBtn = document.querySelector<HTMLButtonElement>("#measure")!;
const playBtn = document.querySelector<HTMLButtonElement>("#play")!;
const filterEl = document.querySelector<HTMLInputElement>("#filter")!;
const kindsEl = document.querySelector<HTMLElement>("#kinds")!;
const cardEl = document.querySelector<HTMLElement>("#card")!;
const lightboxEl = document.querySelector<HTMLElement>("#lightbox")!;
const lbImg = document.querySelector<HTMLImageElement>("#lb-img")!;
const lbCap = document.querySelector<HTMLElement>("#lb-cap")!;
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector<T>(sel)!;
const params = new URLSearchParams(location.search);
/** metres per scene unit in VR (?mpu=), and VR point thinning (?xrstride=, 1 = every point) */
const MPU = Number(params.get("mpu")) || METRES_PER_UNIT_GUESS;
const XR_STRIDE = Math.max(1, Number(params.get("xrstride")) || 2);
/** VR thins more points on its own when the headset misses frames, unless ?xrstride= pins the density */
const XR_ADAPT = !params.has("xrstride");
const XR_MAX_STRIDE = 6;
const SOURCE_LABEL: Record<Source, string> = { scan: "Scan", model: "Model", overlay: "Overlay", wireframe: "Wireframe" };

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0d14);
const camera = new THREE.PerspectiveCamera(FOV, 1, 0.02, 200);
const controls = new OrbitControls(camera, renderer.domElement);
// HTML labels pinned to 3D points (distances); drawn after each WebGL render, not in VR
const labels = new CSS2DRenderer();
labels.domElement.id = "labels";
canvas.after(labels.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.35; // a little smoothing without a long glide (as in the 3D Model Anything viewer)
controls.zoomToCursor = true;
controls.screenSpacePanning = true;

let cloud: BuildCloud | undefined;
let xr: XrWalk | undefined;
let state: ViewState;
let cutManual = false;
let nearOn = true;
/** Points (the dot cloud) or Splats (Gaussian splats via Spark, downloaded on first use) */
type RenderMode = "points" | "splats";
let renderMode: RenderMode = params.get("render") === "splats" ? "splats" : "points";
let splats: SplatLayer | undefined;
let splatsLoading: Promise<void> | null = null;
let grid: THREE.GridHelper | undefined;
let measuring = false;
let dirty = true;
const proximity = new ProximityView();
const measure = new MeasureView(MPU);
scene.add(proximity.group, measure.group);
const invalidate = (): void => {
  dirty = true;
};
controls.addEventListener("change", invalidate);

let toastTimer = 0;
function toast(text: string, ms = 3500): void {
  toastEl.textContent = text;
  toastEl.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => (toastEl.hidden = true), ms);
}

function setPanelOpen(open: boolean): void {
  panelEl.classList.toggle("collapsed", !open);
  panelToggle.setAttribute("aria-expanded", String(open));
}

function resize(): void {
  if (renderer.xr.isPresenting) return; // the headset owns the framebuffer
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  labels.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  cloud?.setViewportHeight(renderer.getDrawingBufferSize(new THREE.Vector2()).y);
  invalidate();
}
window.addEventListener("resize", resize);

/** Dollhouse: hide everything above the cut while the camera is above the room (or when forced on). */
function autoCut(meta: SceneMeta): boolean {
  if (xr?.presenting) return false; // standing in the room: keep the ceiling and the pipe band
  return cutManual || camera.position.y > meta.room_bounds.max[1];
}

function flyTo(box: THREE.Box3, dir = new THREE.Vector3(0.9, 0.8, 1.1), fill = 0.6): void {
  const { position, target } = frameBox(box, dir, FOV, camera.aspect, fill);
  camera.position.copy(position);
  controls.target.copy(target);
  controls.update();
  invalidate();
}

function syncUrl(meta: SceneMeta): void {
  const url = new URL(location.href);
  writeState(url.searchParams, state, meta);
  if (renderMode === "splats") url.searchParams.set("render", "splats");
  else url.searchParams.delete("render");
  history.replaceState(null, "", url);
}

/** Push the view state into the point passes and, in splat mode, into the splat meshes. */
function applyLayers(meta: SceneMeta, cut = autoCut(meta)): void {
  const useSplats = renderMode === "splats" && !!splats?.ready;
  cloud!.pointsVisible = !useSplats;
  cloud!.apply({ ...state, cut });
  splats?.show(useSplats);
  if (grid) grid.visible = !useSplats; // splats write no depth, so the grid would show through the floor
  if (useSplats) splats!.apply({ ...state, cut });
}

function setRender(meta: SceneMeta, mode: RenderMode): void {
  renderMode = mode;
  render(meta);
  if (mode !== "splats" || splats?.ready || splatsLoading) return;
  const btn = document.querySelector<HTMLButtonElement>('#render button[data-render="splats"]')!;
  btn.textContent = "Splats …";
  let shown = -1;
  let layer: SplatLayer | undefined;
  splatsLoading = import("./splats")
    .then(({ SplatLayer }) => {
      layer = new SplatLayer(meta, buildFromUrl(params));
      scene.add(layer.group);
      return layer.load(renderer, scene, invalidate, (f) => {
        const pct = Math.floor(f * 100);
        if (pct === shown) return;
        shown = pct;
        btn.textContent = `Splats ${pct}%`;
      });
    })
    .then(() => {
      if (!layer) return;
      splats = layer;
      layer.setXr(!!xr?.presenting);
      btn.textContent = "Splats";
      toast(`${fmt(meta.count)} Gaussian splats loaded`, 2500);
      render(meta);
    })
    .catch((err: unknown) => {
      if (layer) scene.remove(layer.group);
      btn.textContent = "Splats";
      renderMode = "points";
      render(meta);
      toast(`Splats: ${err instanceof Error ? err.message : String(err)}`, 7000);
      console.error(err);
    })
    .finally(() => (splatsLoading = null));
}

function render(meta: SceneMeta): void {
  if (!cloud) return;
  applyLayers(meta);
  for (const b of document.querySelectorAll<HTMLButtonElement>("#render button")) {
    b.setAttribute("aria-pressed", String(b.dataset.render === renderMode));
  }
  for (const b of document.querySelectorAll<HTMLButtonElement>("#source button")) {
    b.setAttribute("aria-pressed", String(b.dataset.source === state.source));
  }
  for (const b of document.querySelectorAll<HTMLButtonElement>("#style button")) {
    b.setAttribute("aria-pressed", String(b.dataset.style === state.style));
  }
  cutBtn.setAttribute("aria-pressed", String(cutManual));
  boxesBtn.setAttribute("aria-pressed", String(state.boxes));
  nearBtn.setAttribute("aria-pressed", String(nearOn));
  measureBtn.setAttribute("aria-pressed", String(measuring));
  playBtn.setAttribute("aria-pressed", String(playTimer !== 0));
  canvas.classList.toggle("measuring", measuring);
  updateCard(meta);
  uptoEl.value = String(state.upto);
  const last = meta.parts[state.upto - 1];
  uptoLabel.textContent = `${state.upto} / ${meta.parts.length}${last ? ` · ${last.label}` : ""}`;
  for (const li of partsEl.querySelectorAll<HTMLLIElement>("li")) {
    const seq = Number(li.dataset.seq);
    li.classList.toggle("selected", seq === state.selected);
    li.classList.toggle("future", seq > state.upto);
  }
  const built = meta.parts.slice(0, state.upto).reduce((a, p) => a + p.count, 0);
  statsEl.textContent =
    `${fmt(meta.count)} points · ${fmt(built)} in ${state.upto} accepted parts · ` +
    `${fmt(meta.removed_count)} removed by cleaning · ${meta.source.file}`;
  syncUrl(meta);
  invalidate();
}

function set(meta: SceneMeta, patch: Partial<ViewState>): void {
  state = { ...state, ...patch };
  render(meta);
}

function select(meta: SceneMeta, seq: number, fly = true): void {
  if (seq === state.selected || seq <= 0) {
    set(meta, { selected: 0 });
    return;
  }
  const p = meta.parts[seq - 1];
  set(meta, { selected: seq, upto: Math.max(state.upto, seq) });
  if (p && fly) flyTo(partBox(p), undefined, 0.45);
  if (matchMedia("(max-width: 640px)").matches && !playTimer) setPanelOpen(false); // the card takes the space
  partsEl.querySelector(`li[data-seq="${seq}"]`)?.scrollIntoView({ block: "nearest" });
}

/** "Pump 1" card: facts, approval images and nearest parts; also drives the 3D proximity lines. */
let cardKey = "";
function updateCard(meta: SceneMeta): void {
  const sel = state.selected > 0 && state.selected <= state.upto ? meta.parts[state.selected - 1] : undefined;
  const key = sel ? `${sel.seq}|${state.upto}|${nearOn}` : "";
  if (key === cardKey) return;
  cardKey = key;
  cardEl.hidden = !sel;
  if (!sel) {
    proximity.clear();
    return;
  }
  const near = neighbours(meta, sel, state.upto);
  if (nearOn) proximity.show(near, MPU);
  else proximity.clear();

  const b = sel.bbox;
  const size = [0, 1, 2].map((k) => b.max[k] - b.min[k]);
  const centre = [0, 1, 2].map((k) => (b.max[k] + b.min[k]) / 2);
  const lift = b.min[1] - meta.floor_y;
  $("#card-seq").textContent = `#${String(sel.seq).padStart(2, "0")}`;
  $("#card-title").textContent = sel.label;
  $("#card-kind").textContent = sel.kind;
  const facts: [string, string, string?][] = [
    ["Size", `${size.map((v) => v.toFixed(2)).join(" × ")} u`, `≈ ${size.map((v) => (v * MPU).toFixed(2)).join(" × ")} m (x × y × z)`],
    ["Centre", `(${centre.map((v) => v.toFixed(2)).join(", ")}) u`],
    ["Height", lift < 0.05 ? "stands on the floor" : `${lift.toFixed(2)} u above the floor`, lift < 0.05 ? undefined : `≈ ${(lift * MPU).toFixed(2)} m`],
    ["Points", fmt(sel.count)],
  ];
  if (sel.accepted_at) {
    const when = new Date(sel.accepted_at);
    const t = Number.isNaN(when.getTime()) ? sel.accepted_at : when.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
    facts.push(["Accepted", `step ${String(sel.step).padStart(4, "0")} · ${t}`]);
  } else facts.push(["Accepted", `step ${String(sel.step).padStart(4, "0")}`]);
  $("#card-facts").replaceChildren(
    ...facts.flatMap(([k, v, sub]) => {
      const dt = document.createElement("dt");
      dt.textContent = k;
      const dd = document.createElement("dd");
      dd.textContent = v;
      if (sub) {
        const small = document.createElement("small");
        small.textContent = ` ${sub}`;
        dd.append(document.createElement("br"), small);
      }
      return [dt, dd];
    }),
  );

  const images = sel.images ?? [];
  $("#card-images-wrap").hidden = images.length === 0;
  $("#card-images").replaceChildren(
    ...images.map((name, i) => {
      const btn = document.createElement("button");
      btn.title = name;
      btn.innerHTML = `<img loading="lazy" alt="" /><span class="no"></span>`;
      const img = btn.querySelector("img")!;
      img.src = `/api/images/${encodeURIComponent(name)}`;
      img.alt = `approval image ${name}`;
      img.addEventListener("error", () => btn.remove(), { once: true });
      btn.querySelector(".no")!.textContent = name.slice(0, 4);
      btn.addEventListener("click", () => openLightbox(images, i));
      return btn;
    }),
  );

  $("#card-near-wrap").hidden = near.length === 0;
  $("#card-near").replaceChildren(
    ...near.map((n) => {
      const li = document.createElement("li");
      li.tabIndex = 0;
      li.innerHTML = `<span class="n"></span><span class="d"></span>`;
      li.querySelector(".n")!.textContent = n.part.label;
      li.querySelector(".d")!.textContent = fmtGap(n.gap, MPU);
      const go = () => select(meta, n.part.seq);
      li.addEventListener("click", go);
      li.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && go());
      return li;
    }),
  );
}

let lb: { images: string[]; i: number } | null = null;
function openLightbox(images: string[], i: number): void {
  lb = { images, i: (i + images.length) % images.length };
  const name = lb.images[lb.i];
  lbImg.src = `/api/images/${encodeURIComponent(name)}`;
  lbImg.alt = `approval image ${name}`;
  lbCap.textContent = `${lb.i + 1} / ${images.length} · ${name}`;
  lightboxEl.hidden = false;
}
function closeLightbox(): void {
  lb = null;
  lightboxEl.hidden = true;
}
function wireLightbox(): void {
  $("#lb-prev").addEventListener("click", () => lb && openLightbox(lb.images, lb.i - 1));
  $("#lb-next").addEventListener("click", () => lb && openLightbox(lb.images, lb.i + 1));
  $("#lb-close").addEventListener("click", closeLightbox);
  lightboxEl.addEventListener("click", (e) => e.target === lightboxEl && closeLightbox());
}

/** Parts list: free-text filter plus one chip per kind. */
function wireFilter(meta: SceneMeta): void {
  const kinds = [...new Set(meta.parts.map((p) => p.kind))];
  let kind = "";
  const chip = (k: string, label: string, n: number) => {
    const b = document.createElement("button");
    b.dataset.kind = k;
    b.innerHTML = `<span></span><span class="n"></span>`;
    b.firstElementChild!.textContent = label;
    b.lastElementChild!.textContent = String(n);
    b.addEventListener("click", () => {
      kind = k;
      apply();
    });
    return b;
  };
  kindsEl.replaceChildren(chip("", "all", meta.parts.length), ...kinds.map((k) => chip(k, k, meta.parts.filter((p) => p.kind === k).length)));
  const empty = document.createElement("li");
  empty.className = "empty";
  empty.textContent = "no part matches";
  const apply = () => {
    const q = filterEl.value.trim().toLowerCase();
    let shown = 0;
    for (const li of partsEl.querySelectorAll<HTMLLIElement>("li[data-seq]")) {
      const p = meta.parts[Number(li.dataset.seq) - 1];
      const ok = (!kind || p.kind === kind) && (!q || `${p.label} ${p.name} ${p.kind}`.toLowerCase().includes(q));
      li.classList.toggle("filtered", !ok);
      if (ok) shown++;
    }
    for (const b of kindsEl.querySelectorAll<HTMLButtonElement>("button")) b.setAttribute("aria-pressed", String(b.dataset.kind === kind));
    if (shown) empty.remove();
    else partsEl.append(empty);
  };
  filterEl.addEventListener("input", apply);
  filterEl.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      filterEl.value = "";
      apply();
      filterEl.blur();
    }
  });
  apply();
}

/** ▶ Replay: parts appear one by one (newest highlighted) while the camera orbits the room slowly. */
let playTimer = 0;
const PLAY_MS = 900;
function stopPlay(meta: SceneMeta): void {
  if (!playTimer) return;
  clearInterval(playTimer);
  playTimer = 0;
  controls.autoRotate = false;
  render(meta);
}
function togglePlay(meta: SceneMeta): void {
  if (playTimer) return stopPlay(meta);
  const n = meta.parts.length;
  if (!n) return;
  measure.clear();
  if (state.upto >= n) set(meta, { upto: 0, selected: 0 });
  flyTo(roomBox(meta));
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.9;
  playTimer = window.setInterval(() => {
    if (state.upto >= n) {
      stopPlay(meta);
      set(meta, { selected: 0 });
      return;
    }
    const next = state.upto + 1;
    set(meta, { upto: next, selected: next });
  }, PLAY_MS);
  render(meta);
}

function setMeasuring(meta: SceneMeta, on: boolean): void {
  measuring = on;
  if (!on) measure.clear();
  else toast("measure: click two points on the scan · M or Esc to stop", 4000);
  tipEl.hidden = true;
  render(meta);
}

/** The part under a screen point (CSS px), honouring the replay slider and the dollhouse cut. */
function partAt(meta: SceneMeta, x: number, y: number) {
  const rect = canvas.getBoundingClientRect();
  const ndc = new THREE.Vector2(((x - rect.left) / rect.width) * 2 - 1, -((y - rect.top) / rect.height) * 2 + 1);
  const ray = new THREE.Raycaster();
  ray.setFromCamera(ndc, camera);
  const cutY = autoCut(meta) ? (meta.dollhouse_cut_y ?? meta.room_bounds.max[1]) : undefined;
  return pickPart(ray.ray, meta, state.upto, cutY);
}

/** Click or tap a part in the room to select it (a drag still orbits); hover shows its name with a mouse. */
function wirePicking(meta: SceneMeta): void {
  let down: { x: number; y: number; t: number } | null = null;
  canvas.addEventListener("pointerdown", (e) => {
    down = e.isPrimary ? { x: e.clientX, y: e.clientY, t: performance.now() } : null;
    controls.autoRotate = false; // grabbing the view stops the replay's orbit (the replay itself keeps going)
  });
  canvas.addEventListener("pointerup", (e) => {
    if (!down || !e.isPrimary || e.button !== 0) return;
    const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
    const quick = performance.now() - down.t < 500;
    down = null;
    if (moved > 6 || !quick) return;
    if (measuring) {
      const rect = canvas.getBoundingClientRect();
      const ndc = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      const rc = new THREE.Raycaster();
      rc.setFromCamera(ndc, camera);
      const radPerPx = THREE.MathUtils.degToRad(camera.fov) / rect.height;
      const p = pickPoint(cloud!, { ...state, cut: autoCut(meta) }, rc.ray, radPerPx);
      if (!p) return toast("no scan point there: click on the cloud", 2000);
      const d = measure.add(p);
      if (d === null) toast("now click the second point", 2000);
      else toastEl.hidden = true; // the label on the line says it all
      invalidate();
      return;
    }
    const hit = partAt(meta, e.clientX, e.clientY);
    if (hit) select(meta, hit.part.seq);
  });
  canvas.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse" || e.buttons || measuring) {
      tipEl.hidden = true;
      return;
    }
    const hit = partAt(meta, e.clientX, e.clientY);
    canvas.style.cursor = hit ? "pointer" : "";
    tipEl.hidden = !hit;
    if (!hit) return;
    tipEl.textContent = `${hit.part.label} · ${hit.part.kind}`;
    tipEl.style.transform = `translate(${e.clientX + 14}px, ${e.clientY + 14}px)`;
  });
  canvas.addEventListener("pointerleave", () => (tipEl.hidden = true));
}

/** The current camera and state as a capture.html URL (same params, so the snapshot matches what is on screen). */
function snapshotUrl(meta: SceneMeta): string {
  const url = new URL("capture.html", location.href);
  writeState(url.searchParams, state, meta);
  const f = (v: THREE.Vector3) => [v.x, v.y, v.z].map((c) => c.toFixed(3)).join(",");
  url.searchParams.set("cam", f(camera.position));
  url.searchParams.set("look", f(controls.target));
  url.searchParams.set("fov", String(FOV));
  url.searchParams.set("size", "1400x900");
  if (autoCut(meta)) url.searchParams.set("dollhouse", "1");
  return url.toString();
}

function buildPanel(meta: SceneMeta): void {
  uptoEl.max = String(meta.parts.length);
  partsEl.replaceChildren(
    ...meta.parts.map((p) => {
      const li = document.createElement("li");
      li.dataset.seq = String(p.seq);
      li.tabIndex = 0;
      li.innerHTML = `<span class="seq mono">${String(p.seq).padStart(2, "0")}</span>
        <span class="name">${p.label}</span><span class="kind mono" data-kind="${p.kind}">${p.kind}</span>
        <span class="count mono">${fmt(p.count)}</span>`;
      li.addEventListener("click", () => {
        stopPlay(meta);
        select(meta, p.seq);
      });
      li.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") select(meta, p.seq);
      });
      return li;
    }),
  );
  uptoEl.addEventListener("input", () => {
    stopPlay(meta);
    set(meta, { upto: Number(uptoEl.value) });
  });
}

function wireControls(meta: SceneMeta): void {
  for (const b of document.querySelectorAll<HTMLButtonElement>("#source button")) {
    b.addEventListener("click", () => set(meta, { source: b.dataset.source as Source }));
  }
  for (const b of document.querySelectorAll<HTMLButtonElement>("#style button")) {
    b.addEventListener("click", () => set(meta, { style: b.dataset.style === "redgrey" ? "redgrey" : "true" }));
  }
  for (const b of document.querySelectorAll<HTMLButtonElement>("#render button")) {
    b.addEventListener("click", () => setRender(meta, b.dataset.render === "splats" ? "splats" : "points"));
  }
  cutBtn.addEventListener("click", () => {
    cutManual = !cutManual;
    render(meta);
  });
  boxesBtn.addEventListener("click", () => set(meta, { boxes: !state.boxes }));
  snapBtn.addEventListener("click", () => window.open(snapshotUrl(meta), "_blank"));
  homeBtn.addEventListener("click", () => {
    set(meta, { selected: 0 });
    flyTo(roomBox(meta));
  });
  panelToggle.addEventListener("click", () => setPanelOpen(panelEl.classList.contains("collapsed")));
  nearBtn.addEventListener("click", () => {
    nearOn = !nearOn;
    render(meta);
  });
  measureBtn.addEventListener("click", () => setMeasuring(meta, !measuring));
  playBtn.addEventListener("click", () => togglePlay(meta));
  $("#card-close").addEventListener("click", () => set(meta, { selected: 0 }));
  window.addEventListener("keydown", (e) => {
    if (!lightboxEl.hidden) {
      if (e.key === "Escape") closeLightbox();
      else if (e.key === "ArrowRight" && lb) openLightbox(lb.images, lb.i + 1);
      else if (e.key === "ArrowLeft" && lb) openLightbox(lb.images, lb.i - 1);
      return;
    }
    if (e.target instanceof HTMLInputElement || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target instanceof HTMLButtonElement && (e.key === " " || e.key === "Enter")) return;
    const n = Number(e.key);
    if (n >= 1 && n <= SOURCES.length) set(meta, { source: SOURCES[n - 1] });
    else if (e.key === "Escape") {
      if (measuring && measure.points.length) {
        measure.clear();
        invalidate();
      } else if (measuring) setMeasuring(meta, false);
      else set(meta, { selected: 0 });
    } else if (e.key === " ") {
      e.preventDefault();
      togglePlay(meta);
    } else if (e.key === "m" || e.key === "M") setMeasuring(meta, !measuring);
    else if (e.key === "g" || e.key === "G") setRender(meta, renderMode === "splats" ? "points" : "splats");
    else if (e.key === "n" || e.key === "N") {
      nearOn = !nearOn;
      render(meta);
    } else if (e.key === "/") {
      e.preventDefault();
      setPanelOpen(true);
      filterEl.focus();
    } else if (e.key === "ArrowRight") {
      stopPlay(meta);
      set(meta, { upto: Math.min(meta.parts.length, state.upto + 1) });
    } else if (e.key === "ArrowLeft") {
      stopPlay(meta);
      set(meta, { upto: Math.max(0, state.upto - 1) });
    }
    else if (e.key === "d" || e.key === "D") {
      cutManual = !cutManual;
      render(meta);
    } else if (e.key === "b" || e.key === "B") set(meta, { boxes: !state.boxes });
    else if (e.key === "p" || e.key === "P") window.open(snapshotUrl(meta), "_blank");
    else if (e.key === "Home") flyTo(roomBox(meta));
  });
}

async function main(): Promise<void> {
  const { meta, geometry } = await loadScene(buildFromUrl(params));
  cloud = new BuildCloud(meta, geometry);
  scene.add(cloud.group);
  const room = roomBox(meta);
  grid = new THREE.GridHelper(Math.ceil(room.getSize(new THREE.Vector3()).x + 2), 20, 0x2a3350, 0x1a2036);
  grid.position.set((room.min.x + room.max.x) / 2, meta.floor_y - 0.005, (room.min.z + room.max.z) / 2);
  scene.add(grid);

  state = readState(params, meta);
  buildPanel(meta);
  wireControls(meta);
  wireFilter(meta);
  wireLightbox();
  wirePicking(meta);
  setupXr(meta);
  // small screens start with the build list folded away so the room is visible
  if (matchMedia("(max-width: 640px), (max-height: 500px)").matches) setPanelOpen(false);
  resize();
  const sel = meta.parts[state.selected - 1];
  if (sel) flyTo(partBox(sel), undefined, 0.45);
  else flyTo(room);
  render(meta);
  if (renderMode === "splats") setRender(meta, "splats"); // ?render=splats: start the download right away

  if (import.meta.env.DEV) {
    Object.assign(window, { __a2b: { renderer, scene, camera, controls, cloud, meta, xr, splats: () => splats } });
  }
  let wasCut = autoCut(meta);
  let lastT = 0;
  let eyeH = 0;
  loadingEl.classList.add("done");
  setTimeout(() => (loadingEl.hidden = true), 450);
  if (matchMedia("(pointer: coarse)").matches) toast("drag to orbit · pinch to zoom · tap a part to fly to it");
  renderer.setAnimationLoop((t: number) => {
    const dt = lastT ? Math.min((t - lastT) / 1000, 0.1) : 0;
    lastT = t;
    if (xr?.presenting) {
      // the headset needs a frame every refresh: no idle skipping in VR
      xr.update(dt);
      adaptStride(meta, dt);
      const h = xr.eyeHeight();
      if (h && h !== eyeH) cloud!.setViewportHeight((eyeH = h));
      renderer.render(scene, camera);
      return;
    }
    eyeH = 0;
    controls.update();
    const cut = autoCut(meta);
    if (cut !== wasCut) {
      wasCut = cut;
      applyLayers(meta, cut);
      dirty = true;
    }
    if (!dirty) return; // idle rendering: 1.6 M points only redraw when something changed
    dirty = false;
    renderer.render(scene, camera);
    labels.render(scene, camera);
  });
}

/**
 * Keep VR smooth on an untested scan size: when frames run long (under ~55 fps on a 72 Hz headset) for a second and a
 * half, draw fewer points. Only ever thins (no oscillation); every VR session starts again from XR_STRIDE.
 */
let xrStride = XR_STRIDE;
let slowFor = 0;
let frameAvg = 0;
function adaptStride(meta: SceneMeta, dt: number): void {
  if (!XR_ADAPT || !cloud || dt <= 0) return;
  frameAvg = frameAvg ? frameAvg * 0.9 + dt * 0.1 : dt;
  slowFor = frameAvg > 1 / 55 ? slowFor + dt : 0;
  if (slowFor > 1.5 && xrStride < XR_MAX_STRIDE) {
    xrStride++;
    cloud.setStride(xrStride);
    render(meta);
    slowFor = 0;
    frameAvg = 0;
  }
}

/** WebXR walk-through (Quest 3): the Enter VR button, and what changes while the headset is on. */
function setupXr(meta: SceneMeta): void {
  let before: Source | null = null;
  const order: Source[] = ["scan", "model", "overlay"];
  const walk = new XrWalk(
    renderer,
    scene,
    camera,
    meta,
    {
      onStart() {
        controls.enabled = false;
        // inside the room the real scan reads best; overlay/wireframe haze is for looking from outside
        before = state.source;
        if (state.source === "overlay" || state.source === "wireframe") state = { ...state, source: "scan" };
        xrStride = XR_STRIDE;
        slowFor = frameAvg = 0;
        cloud!.setStride(xrStride);
        cloud!.sizeScale = MPU; // view space is metres in XR, point sizes are in scene units
        splats?.setXr(true);
        render(meta);
        vrLabel.textContent = "Exit VR";
      },
      onEnd() {
        controls.enabled = true;
        cloud!.setStride(1);
        cloud!.sizeScale = 1;
        splats?.setXr(false);
        if (before) state = { ...state, source: before };
        before = null;
        resize();
        controls.update();
        render(meta);
        vrLabel.textContent = "Enter VR";
      },
      cycleSource() {
        const i = order.indexOf(state.source);
        set(meta, { source: order[(i + 1) % order.length] });
      },
      toggleBoxes() {
        set(meta, { boxes: !state.boxes });
      },
      toggleRender() {
        setRender(meta, renderMode === "splats" ? "points" : "splats");
      },
      select(seq) {
        select(meta, seq, false);
      },
      status() {
        const last = meta.parts[state.upto - 1];
        const sel = meta.parts[state.selected - 1];
        const density = xrStride > 1 ? ` · 1/${xrStride} pts` : "";
        const as = renderMode === "splats" && splats?.ready ? " splats" : "";
        return [
          `${SOURCE_LABEL[state.source]}${as} · ${state.upto}/${meta.parts.length} parts${as ? "" : density}`,
          sel ? `selected: ${sel.label}` : last ? `latest: ${last.label} · 1 u ≈ ${MPU} m` : `1 u ≈ ${MPU} m`,
        ];
      },
    },
    { metresPerUnit: MPU, focus: () => meta.parts[state.selected - 1], upto: () => state.upto },
  );
  xr = walk;
  vrBtn.addEventListener("click", () => {
    walk.toggle().catch((err: unknown) => toast(`VR: ${err instanceof Error ? err.message : String(err)}`, 6000));
  });
  vrSupported().then((ok) => {
    if (ok) {
      vrBtn.hidden = false;
      return;
    }
    // Quest Browser hides WebXR on plain http:// over the LAN: say why instead of showing nothing
    if (/OculusBrowser|Quest/i.test(navigator.userAgent) && !window.isSecureContext) {
      vrBtn.hidden = false;
      vrBtn.disabled = true;
      vrLabel.textContent = "VR needs HTTPS";
      vrBtn.title = "open this page over https:// (make web-vr) or via adb reverse on localhost";
    }
  });
}

main().catch((err: unknown) => {
  const msg = err instanceof Error ? err.message : String(err);
  statsEl.textContent = msg;
  loadingEl.classList.add("error");
  loadingText.textContent = msg;
  console.error(err);
});
