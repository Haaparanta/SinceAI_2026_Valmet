/**
 * Snapshot page: one deterministic render of the build, driven only by the URL, for scripted screenshots
 * (web/tools/snap.mjs). Ported from the 3D Model Anything capture page (apps/room-viewer/tools/capture.ts, MIT, Wes Bos):
 * same orthographic views, section cut, metre grid and readiness flag, applied to our point cloud.
 *
 * /capture.html?<state>&<camera>&<caption>
 *   state    src=scan|model|overlay|wireframe  part=<name|seq>  upto=<name|seq>  style=true|redgrey|origin  boxes=1  dollhouse=1
 *            scene=auto|both (default: the manual build)
 *            ps=<point size scale, default 1>
 *   camera   view=top|up|n|s|e|w [ppm=120] [cut=<coord>] [nogrid]     orthographic plan / elevation with a grid
 *            cam=x,y,z&look=x,y,z [fov=50] [size=WxH]                   perspective
 *            (neither)  frame the selected part (or the room; frame=room forces it) from dir=x,y,z
 *                       [fill=0.45 part / 0.6 room: larger = tighter] [fov=50] [size=WxH]
 *   caption  title=  sub=  badge=  legend=0
 * When done: body[data-ready="1"], body[data-info] = JSON (size, camera, visible part names).
 */
import * as THREE from "three";
import { BuildCloud, buildFromUrl, frameBox, fullChunk, loadScene, looksFor, partBox, readState, roomBox, type ViewState } from "./scene";

type Axis = "x" | "y" | "z";
interface ViewDef {
  dir: THREE.Vector3;
  up: THREE.Vector3;
  h: [Axis, number, number, number];
  v: [Axis, number, number, number];
  cut: number;
}

const params = new URLSearchParams(location.search);
const vec = (s: string): THREE.Vector3 => new THREE.Vector3(...s.split(",").map(Number));

function legendFor(s: ViewState, hasSel: boolean): string {
  if (s.style === "redgrey") return "red = selected · grey (25 %) = built · scan points hidden";
  if (s.style === "origin") return `cyan = manual build · amber = automatic build${hasSel ? " · red = selected" : ""} · rest of scan faint`;
  const l = looksFor(s);
  const pct = (a: number) => `${Math.round(a * 100)} %`;
  const parts = [
    hasSel ? `selected ${pct(l[2].alpha)}` : "",
    `built parts ${pct(l[1].alpha)}`,
    l[0].alpha > 0 ? `rest of scan ${pct(l[0].alpha)}` : "scan hidden",
  ].filter(Boolean);
  return `${s.source.toUpperCase()} · true colour · ${parts.join(" · ")}${s.boxes || s.source === "wireframe" ? " · boxes" : ""}`;
}

function badgeColour(text: string): string {
  const t = text.toUpperCase();
  if (/FAIL|REJECT/.test(t)) return "#ff2d55";
  if (/ACCEPT|APPROV|OK/.test(t)) return "#2ee59d";
  if (/PROPOS|PENDING|REPLACED/.test(t)) return "#ffc94d";
  return "#9de2f0";
}

async function main(): Promise<void> {
  const { meta, geometry } = await loadScene(buildFromUrl(params));
  const state = readState(params, meta);
  const cloud = new BuildCloud(meta, fullChunk(meta, geometry));
  cloud.sizeScale = Number(params.get("ps") ?? 1);
  const sel = meta.parts[state.selected - 1];
  const room = roomBox(meta);

  const view = params.get("view");
  const ppm = Number(params.get("ppm") ?? 120);
  const pad = 0.25;
  const X: [number, number] = [room.min.x - pad, room.max.x + pad];
  const Z: [number, number] = [room.min.z - pad, room.max.z + pad];
  const Y: [number, number] = [meta.floor_y - 0.1, room.max.y + 0.45];
  const topCut = meta.dollhouse_cut_y ?? room.max.y - 0.05;
  const views: Record<string, ViewDef> = {
    top: { dir: new THREE.Vector3(0, -1, 0), up: new THREE.Vector3(0, 0, -1), h: ["x", ...X, 1], v: ["z", ...Z, -1], cut: topCut },
    n: { dir: new THREE.Vector3(0, 0, -1), up: new THREE.Vector3(0, 1, 0), h: ["x", ...X, 1], v: ["y", ...Y, 1], cut: room.max.z - 0.1 },
    s: { dir: new THREE.Vector3(0, 0, 1), up: new THREE.Vector3(0, 1, 0), h: ["x", ...X, -1], v: ["y", ...Y, 1], cut: room.min.z + 0.1 },
    e: { dir: new THREE.Vector3(1, 0, 0), up: new THREE.Vector3(0, 1, 0), h: ["z", ...Z, 1], v: ["y", ...Y, 1], cut: room.min.x + 0.1 },
    w: { dir: new THREE.Vector3(-1, 0, 0), up: new THREE.Vector3(0, 1, 0), h: ["z", ...Z, -1], v: ["y", ...Y, 1], cut: room.max.x - 0.1 },
    up: { dir: new THREE.Vector3(0, 1, 0), up: new THREE.Vector3(0, 0, 1), h: ["x", ...X, 1], v: ["z", ...Z, 1], cut: meta.floor_y + 0.05 },
  };
  const def = view ? views[view] : undefined;
  if (view && !def) throw new Error(`view=${view}: use one of ${Object.keys(views).join(", ")}`);

  let W: number;
  let H: number;
  if (def) {
    W = Math.round((def.h[2] - def.h[1]) * ppm);
    H = Math.round((def.v[2] - def.v[1]) * ppm);
  } else {
    [W, H] = (params.get("size") ?? "1400x900").split("x").map(Number);
  }

  const canvas = document.querySelector<HTMLCanvasElement>("#scene")!;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(W, H);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05060a);
  scene.add(cloud.group);
  cloud.setViewportHeight(H);

  let camera: THREE.Camera;
  let camInfo: Record<string, unknown>;
  if (def) {
    const cut = params.has("cut") ? Number(params.get("cut")) : def.cut;
    const [hAxis, hMin, hMax] = def.h;
    const [vAxis, vMin, vMax] = def.v;
    const cam = new THREE.OrthographicCamera(-W / ppm / 2, W / ppm / 2, H / ppm / 2, -H / ppm / 2, 0, 40);
    const center = new THREE.Vector3();
    center[hAxis] = (hMin + hMax) / 2;
    center[vAxis] = (vMin + vMax) / 2;
    const viewAxis: Axis = def.dir.x ? "x" : def.dir.y ? "y" : "z";
    center[viewAxis] = cut; // the camera sits on the section plane: everything between it and the viewer is cut away
    cam.position.copy(center);
    cam.up.copy(def.up);
    cam.lookAt(center.clone().add(def.dir));
    camera = cam;
    camInfo = { view, ppm, cut };
  } else {
    const fov = Number(params.get("fov") ?? 50);
    const cam = new THREE.PerspectiveCamera(fov, W / H, 0.02, 200);
    if (params.has("cam")) {
      cam.position.copy(vec(params.get("cam")!));
      cam.lookAt(vec(params.get("look") ?? "0,0,0"));
    } else {
      const onPart = sel && params.get("frame") !== "room";
      const dir = vec(params.get("dir") ?? "0.9,0.8,1.1");
      const fill = Number(params.get("fill") ?? (onPart ? 0.45 : 0.6));
      const { position, target } = frameBox(onPart ? partBox(sel) : room, dir, fov, W / H, fill);
      cam.position.copy(position);
      cam.lookAt(target);
    }
    camera = cam;
    const r = (v: THREE.Vector3) => [v.x, v.y, v.z].map((c) => +c.toFixed(3));
    camInfo = { cam: r(cam.position), look: r(cam.getWorldDirection(new THREE.Vector3()).add(cam.position)), fov };
  }

  cloud.apply(state);
  renderer.render(scene, camera);

  // A first frame can come out black while shaders compile on a busy GPU: check a grid of pixels and redraw.
  const gl = renderer.getContext();
  const px = new Uint8Array(4);
  const lit = (): boolean => {
    for (let i = 1; i < 6; i++)
      for (let j = 1; j < 6; j++) {
        gl.readPixels(Math.floor((W * i) / 6), Math.floor((H * j) / 6), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
        if (px[0] + px[1] + px[2] > 30) return true;
      }
    return false;
  };
  for (let k = 0; k < 6 && !lit(); k++) {
    await new Promise((r) => setTimeout(r, 250));
    renderer.render(scene, camera);
  }

  // --- grid overlay (orthographic views only), 0.25 u spacing like the original ---------------------------------
  const grid = document.querySelector<HTMLCanvasElement>("#grid")!;
  grid.width = W;
  grid.height = H;
  if (def && !params.has("nogrid")) {
    const ctx = grid.getContext("2d")!;
    const [hAxis, hMin, hMax, hSign] = def.h;
    const [vAxis, vMin, vMax, vSign] = def.v;
    const toPxH = (c: number) => (hSign > 0 ? c - hMin : hMax - c) * ppm;
    const toPxV = (c: number) => (vSign > 0 ? vMax - c : c - vMin) * ppm;
    ctx.font = "12px monospace";
    const lines = (min: number, max: number, draw: (c: number, major: boolean, half: boolean) => void) => {
      for (let c = Math.ceil(min * 4) / 4; c <= max; c += 0.25) {
        draw(c, Math.abs(c - Math.round(c)) < 1e-6, Math.abs(c * 2 - Math.round(c * 2)) < 1e-6);
      }
    };
    lines(hMin, hMax, (c, major, half) => {
      ctx.strokeStyle = major ? "rgba(0,200,255,0.6)" : half ? "rgba(0,200,255,0.3)" : "rgba(0,200,255,0.12)";
      const x = toPxH(c);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
      if (half) {
        ctx.fillStyle = "#0ff";
        ctx.fillText(`${hAxis}${c.toFixed(1)}`, x + 2, 12);
      }
    });
    lines(vMin, vMax, (c, major, half) => {
      ctx.strokeStyle = major ? "rgba(255,200,0,0.6)" : half ? "rgba(255,200,0,0.3)" : "rgba(255,200,0,0.12)";
      const y = toPxV(c);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
      if (half) {
        ctx.fillStyle = "#ff0";
        ctx.fillText(`${vAxis}${c.toFixed(1)}`, 2, y - 2);
      }
    });
  } else grid.style.display = "none";

  // --- caption + badge ------------------------------------------------------------------------------------------
  const caption = document.querySelector<HTMLElement>("#caption")!;
  const add = (cls: string, text: string) => {
    const el = document.createElement("div");
    el.className = cls;
    el.textContent = text;
    caption.append(el);
  };
  if (params.get("title")) add("title", params.get("title")!);
  if (params.get("sub")) add("sub", params.get("sub")!);
  if (params.get("legend") !== "0") {
    const built = meta.parts.slice(0, state.upto);
    add("legend", `${legendFor(state, !!sel)} · ${built.length} parts built${sel ? ` · selected: ${sel.label}` : ""}`);
  }
  const badgeText = params.get("badge") ?? "";
  const badge = document.querySelector<HTMLElement>("#badge")!;
  badge.textContent = badgeText;
  badge.style.background = badgeColour(badgeText);

  document.body.dataset.info = JSON.stringify({
    size: [W, H],
    camera: camInfo,
    state,
    selected: sel?.name ?? null,
    built: meta.parts.slice(0, state.upto).map((p) => p.name),
  });
  document.body.dataset.ready = "1";
}

main().catch((err: unknown) => {
  const msg = err instanceof Error ? err.message : String(err);
  document.body.dataset.error = msg;
  document.body.dataset.ready = "1";
  const pre = document.createElement("pre");
  pre.style.cssText = "color:#ff2d55;padding:12px";
  pre.textContent = msg;
  document.body.append(pre);
  console.error(err);
});
