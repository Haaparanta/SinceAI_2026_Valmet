import "./style.css";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

/** data/derived/scene_points.bin (AGENTS.md S3): uint32 count | float32 xyz*count | uint8 rgb*count, little-endian. */
interface ScenePoints {
  count: number;
  xyz: Float32Array;
  rgb: Uint8Array;
}

/** The part of data/derived/clean_stats.json (pipeline/01_clean.py) the viewer uses. Numbers are never typed in here. */
interface CleanStats {
  total: number;
  kept: number;
  scene_points: number;
  floor_y: number;
  bounds_p1: [number, number, number];
  bounds_p99: [number, number, number];
  units: string;
}

function parseScenePoints(buf: ArrayBuffer): ScenePoints {
  const count = new DataView(buf).getUint32(0, true);
  const expected = 4 + count * 12 + count * 3;
  if (buf.byteLength !== expected) {
    throw new Error(`scene_points.bin is ${buf.byteLength} bytes, expected ${expected} for ${count} points`);
  }
  return { count, xyz: new Float32Array(buf, 4, count * 3), rgb: new Uint8Array(buf, 4 + count * 12, count * 3) };
}

async function fetchPoints(): Promise<ScenePoints> {
  const res = await fetch("/api/scene/points");
  if (!res.ok) {
    throw new Error(`GET /api/scene/points -> ${res.status}. Run \`uv run python pipeline/01_clean.py\` first.`);
  }
  return parseScenePoints(await res.arrayBuffer());
}

async function fetchStats(): Promise<CleanStats | null> {
  try {
    const res = await fetch("/api/scene/stats");
    return res.ok ? ((await res.json()) as CleanStats) : null;
  } catch {
    return null;
  }
}

const fmt = (n: number): string => n.toLocaleString("en-US");

const canvas = document.querySelector<HTMLCanvasElement>("#scene")!;
const statsEl = document.querySelector<HTMLElement>("#stats")!;

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0d14);
const camera = new THREE.PerspectiveCamera(50, 1, 0.05, 500);
camera.up.set(0, 1, 0); // y-up, as measured on the scan
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

function resize(): void {
  const w = window.innerWidth;
  const h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

/** Isometric-ish framing of a box: the snapshot recipe's (+6, +7, +6) offset from the centre (AGENTS.md S3). */
function frame(min: THREE.Vector3, max: THREE.Vector3): void {
  const center = min.clone().add(max).multiplyScalar(0.5);
  camera.position.copy(center).add(new THREE.Vector3(6, 7, 6));
  controls.target.copy(center);
  controls.update();
}

async function main(): Promise<void> {
  const [pts, stats] = await Promise.all([fetchPoints(), fetchStats()]);

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(pts.xyz, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(pts.rgb, 3, true));
  geometry.computeBoundingBox();
  const material = new THREE.PointsMaterial({ size: 0.022, vertexColors: true, sizeAttenuation: true });
  scene.add(new THREE.Points(geometry, material));

  // Frame on the p1..p99 room box from the pipeline (the raw bounding box still holds floaters up to |20| u).
  const box = geometry.boundingBox!;
  const min = stats ? new THREE.Vector3(...stats.bounds_p1) : box.min.clone();
  const max = stats ? new THREE.Vector3(...stats.bounds_p99) : box.max.clone();
  frame(min, max);

  if (stats) {
    const span = Math.max(max.x - min.x, max.z - min.z) + 2;
    const grid = new THREE.GridHelper(span, Math.round(span / 0.5), 0x2a3350, 0x1a2036);
    grid.position.set((min.x + max.x) / 2, stats.floor_y, (min.z + max.z) / 2);
    scene.add(grid);
    const room = [max.x - min.x, max.y - min.y, max.z - min.z].map((v) => v.toFixed(1)).join(" × ");
    statsEl.textContent =
      `POINTS ${fmt(pts.count)} shown · ${fmt(stats.kept)} kept of ${fmt(stats.total)} gaussians` +
      ` · room ${room} u (p1–p99) · floor y ${stats.floor_y.toFixed(2)} u`;
  } else {
    statsEl.textContent = `POINTS ${fmt(pts.count)} shown (clean_stats.json not served)`;
  }
  scene.add(new THREE.AxesHelper(0.5));

  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });
}

main().catch((err: unknown) => {
  statsEl.textContent = err instanceof Error ? err.message : String(err);
  console.error(err);
});
