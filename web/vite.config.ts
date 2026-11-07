import { createReadStream, existsSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import basicSsl from "@vitejs/plugin-basic-ssl";
import { defineConfig, type Plugin } from "vite";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..");
const derived = resolve(repoRoot, "data/derived");

/**
 * Dev-only fallback so `npm run dev` shows the room without the FastAPI running:
 * serves data/derived files at the same paths api/main.py uses. Any other /api/* request goes to the proxy below.
 */
function derivedFiles(): Plugin {
  const routes: Record<string, string> = {
    "/api/scene/points": resolve(derived, "scene_points.bin"),
    "/api/scene/stats": resolve(derived, "clean_stats.json"),
    // scripts/export_viewer_scene.py (the step-by-step build for the viewer and capture.html)
    "/api/viewer/scene.bin": resolve(derived, "viewer/scene.bin"),
    "/api/viewer/scene.json": resolve(derived, "viewer/scene.json"),
  };
  return {
    name: "a2b-derived-files",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const path = (req.url ?? "").split("?")[0];
        // numbered step images, same rule as api/main.py (GET /api/images/{name})
        const img = /^\/api\/images\/(\d{4,}_\d{8}-\d{6}(?:_[\w-]+)?\.png)$/.exec(path);
        const file = img ? resolve(repoRoot, "images", img[1]) : routes[path];
        if (!file || !existsSync(file)) return next();
        const type = file.endsWith(".json") ? "application/json" : file.endsWith(".png") ? "image/png" : "application/octet-stream";
        res.setHeader("Content-Type", type);
        res.setHeader("Content-Length", statSync(file).size);
        res.setHeader("X-A2B-Source", "vite-dev-fallback");
        createReadStream(file).pipe(res);
      });
    },
  };
}

/**
 * VR=1 (`make web-vr`): HTTPS with a self-signed certificate on every network interface, so a Meta Quest 3 on the same
 * Wi-Fi can open https://<laptop-ip>:5173 and enter VR (browsers only expose WebXR on https:// or localhost). Accept the
 * certificate warning once in Quest Browser. With a USB cable, `adb reverse tcp:5173 tcp:5173` + http://localhost works too.
 */
const vr = process.env.VR === "1";

export default defineConfig({
  plugins: [derivedFiles(), ...(vr ? [basicSsl({ name: "a2b-quest" })] : [])],
  build: {
    rollupOptions: {
      input: { main: resolve(here, "index.html"), capture: resolve(here, "capture.html") },
    },
  },
  server: {
    port: 5173,
    host: vr ? true : undefined,
    fs: { allow: [here, resolve(repoRoot, "design")] }, // style.css imports design/cyberpunk-tokens.css
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
