import "./style.css";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  BuildCloud,
  frameBox,
  loadScene,
  METRES_PER_UNIT_GUESS,
  partBox,
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
const params = new URLSearchParams(location.search);
/** metres per scene unit in VR (?mpu=), and VR point thinning (?xrstride=, 1 = every point) */
const MPU = Number(params.get("mpu")) || METRES_PER_UNIT_GUESS;
const XR_STRIDE = Math.max(1, Number(params.get("xrstride")) || 2);
const SOURCE_LABEL: Record<Source, string> = { scan: "Scan", model: "Model", overlay: "Overlay", wireframe: "Wireframe" };

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0d14);
const camera = new THREE.PerspectiveCamera(FOV, 1, 0.02, 200);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.35; // a little smoothing without a long glide (as in the 3D Model Anything viewer)
controls.zoomToCursor = true;
controls.screenSpacePanning = true;

let cloud: BuildCloud | undefined;
let xr: XrWalk | undefined;
let state: ViewState;
let cutManual = false;
let dirty = true;
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
  history.replaceState(null, "", url);
}

function render(meta: SceneMeta): void {
  if (!cloud) return;
  cloud.apply({ ...state, cut: autoCut(meta) });
  for (const b of document.querySelectorAll<HTMLButtonElement>("#source button")) {
    b.setAttribute("aria-pressed", String(b.dataset.source === state.source));
  }
  for (const b of document.querySelectorAll<HTMLButtonElement>("#style button")) {
    b.setAttribute("aria-pressed", String(b.dataset.style === state.style));
  }
  cutBtn.setAttribute("aria-pressed", String(cutManual));
  boxesBtn.setAttribute("aria-pressed", String(state.boxes));
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

function select(meta: SceneMeta, seq: number): void {
  if (seq === state.selected || seq <= 0) {
    set(meta, { selected: 0 });
    return;
  }
  const p = meta.parts[seq - 1];
  set(meta, { selected: seq, upto: Math.max(state.upto, seq) });
  if (p) flyTo(partBox(p), undefined, 0.45);
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
      li.addEventListener("click", () => select(meta, p.seq));
      li.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") select(meta, p.seq);
      });
      return li;
    }),
  );
  uptoEl.addEventListener("input", () => set(meta, { upto: Number(uptoEl.value) }));
}

function wireControls(meta: SceneMeta): void {
  for (const b of document.querySelectorAll<HTMLButtonElement>("#source button")) {
    b.addEventListener("click", () => set(meta, { source: b.dataset.source as Source }));
  }
  for (const b of document.querySelectorAll<HTMLButtonElement>("#style button")) {
    b.addEventListener("click", () => set(meta, { style: b.dataset.style === "redgrey" ? "redgrey" : "true" }));
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
  window.addEventListener("keydown", (e) => {
    if (e.target instanceof HTMLInputElement) return;
    const n = Number(e.key);
    if (n >= 1 && n <= SOURCES.length) set(meta, { source: SOURCES[n - 1] });
    else if (e.key === "Escape") set(meta, { selected: 0 });
    else if (e.key === "ArrowRight") set(meta, { upto: Math.min(meta.parts.length, state.upto + 1) });
    else if (e.key === "ArrowLeft") set(meta, { upto: Math.max(0, state.upto - 1) });
    else if (e.key === "d" || e.key === "D") {
      cutManual = !cutManual;
      render(meta);
    } else if (e.key === "b" || e.key === "B") set(meta, { boxes: !state.boxes });
    else if (e.key === "p" || e.key === "P") window.open(snapshotUrl(meta), "_blank");
    else if (e.key === "Home") flyTo(roomBox(meta));
  });
}

async function main(): Promise<void> {
  const { meta, geometry } = await loadScene();
  cloud = new BuildCloud(meta, geometry);
  scene.add(cloud.group);
  const room = roomBox(meta);
  const grid = new THREE.GridHelper(Math.ceil(room.getSize(new THREE.Vector3()).x + 2), 20, 0x2a3350, 0x1a2036);
  grid.position.set((room.min.x + room.max.x) / 2, meta.floor_y - 0.005, (room.min.z + room.max.z) / 2);
  scene.add(grid);

  state = readState(params, meta);
  buildPanel(meta);
  wireControls(meta);
  setupXr(meta);
  // small screens start with the build list folded away so the room is visible
  if (matchMedia("(max-width: 640px), (max-height: 500px)").matches) setPanelOpen(false);
  resize();
  const sel = meta.parts[state.selected - 1];
  if (sel) flyTo(partBox(sel), undefined, 0.45);
  else flyTo(room);
  render(meta);

  if (import.meta.env.DEV) Object.assign(window, { __a2b: { renderer, scene, camera, controls, cloud, meta, xr } });
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
      cloud!.apply({ ...state, cut });
      dirty = true;
    }
    if (!dirty) return; // idle rendering: 1.6 M points only redraw when something changed
    dirty = false;
    renderer.render(scene, camera);
  });
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
        cloud!.setStride(XR_STRIDE);
        cloud!.sizeScale = MPU; // view space is metres in XR, point sizes are in scene units
        render(meta);
        vrLabel.textContent = "Exit VR";
      },
      onEnd() {
        controls.enabled = true;
        cloud!.setStride(1);
        cloud!.sizeScale = 1;
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
      status() {
        const last = meta.parts[state.upto - 1];
        const sel = meta.parts[state.selected - 1];
        return [
          `${SOURCE_LABEL[state.source]} · ${state.upto}/${meta.parts.length} parts`,
          sel ? `selected: ${sel.label}` : last ? `latest: ${last.label} · 1 u ≈ ${MPU} m` : `1 u ≈ ${MPU} m`,
        ];
      },
    },
    { metresPerUnit: MPU, focus: () => meta.parts[state.selected - 1] },
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
