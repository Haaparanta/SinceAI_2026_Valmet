import "./style.css";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  BuildCloud,
  frameBox,
  loadScene,
  partBox,
  readState,
  roomBox,
  SOURCES,
  writeState,
  type SceneMeta,
  type Source,
  type ViewState,
} from "./scene";
import { XRWalk, xrStatus } from "./xr";

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
const vrBtn = document.querySelector<HTMLButtonElement>("#vr")!;

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0d14);
const camera = new THREE.PerspectiveCamera(FOV, 1, 0.02, 200);
// The camera lives in a rig: identity on the desktop, moved by the XR locomotion (never move the XR camera itself).
const rig = new THREE.Group();
rig.add(camera);
scene.add(rig);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.35; // a little smoothing without a long glide (as in the 3D Model Anything viewer)
controls.zoomToCursor = true;
controls.screenSpacePanning = true;

let cloud: BuildCloud | undefined;
let xr: XRWalk | undefined;
let state: ViewState;
let cutManual = false;
let dirty = true;
const invalidate = (): void => {
  dirty = true;
};
controls.addEventListener("change", invalidate);

function resize(): void {
  if (renderer.xr.isPresenting) return; // the XR layer owns the size while in VR
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  cloud?.setViewportHeight(renderer.getDrawingBufferSize(new THREE.Vector2()).y);
  invalidate();
}
window.addEventListener("resize", resize);

/** Dollhouse: hide everything above the cut while the camera is above the room (or when forced on). */
function autoCut(meta: SceneMeta): boolean {
  if (renderer.xr.isPresenting) return cutManual; // inside the room in VR: only on request
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
  xr?.refreshPanel();
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
        <span class="name">${p.label}</span><span class="kind mono">${p.kind}</span>
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

async function setupVrButton(): Promise<void> {
  const status = await xrStatus();
  vrBtn.disabled = !status.ok;
  vrBtn.title = status.ok ? "walk the room in a Quest 3 (WebXR)" : status.reason;
  vrBtn.dataset.status = status.ok ? "ok" : "unavailable";
  vrBtn.addEventListener("click", async () => {
    if (!xr || xr.presenting) return;
    try {
      await xr.enter();
    } catch (err) {
      statsEl.textContent = `VR failed: ${err instanceof Error ? err.message : String(err)}`;
    }
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

  state = readState(new URLSearchParams(location.search), meta);
  buildPanel(meta);
  wireControls(meta);
  resize();
  const sel = meta.parts[state.selected - 1];
  if (sel) flyTo(partBox(sel), undefined, 0.45);
  else flyTo(room);
  render(meta);

  xr = new XRWalk({
    renderer,
    camera,
    rig,
    cloud,
    meta,
    getState: () => state,
    setState: (patch) => set(meta, patch),
    startPose: () => ({ target: controls.target.clone(), forward: camera.getWorldDirection(new THREE.Vector3()) }),
    toggleCut: () => {
      cutManual = !cutManual;
      render(meta);
    },
    onStart: () => {
      controls.enabled = false;
      document.body.classList.add("in-xr");
      render(meta);
    },
    onEnd: () => {
      controls.enabled = true;
      document.body.classList.remove("in-xr");
      resize();
      controls.update();
      render(meta);
    },
  });
  void setupVrButton();

  if (import.meta.env.DEV) Object.assign(window, { __a2b: { renderer, scene, camera, controls, cloud, meta, rig, xr } });
  let wasCut = autoCut(meta);
  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    const dt = Math.min(clock.getDelta(), 0.1);
    if (renderer.xr.isPresenting) {
      xr!.update(dt); // VR renders every frame
      renderer.render(scene, camera);
      return;
    }
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

main().catch((err: unknown) => {
  statsEl.textContent = err instanceof Error ? err.message : String(err);
  console.error(err);
});
