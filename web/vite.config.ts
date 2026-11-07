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
        const file = routes[(req.url ?? "").split("?")[0]];
        if (!file || !existsSync(file)) return next();
        res.setHeader("Content-Type", file.endsWith(".json") ? "application/json" : "application/octet-stream");
        res.setHeader("Content-Length", statSync(file).size);
        res.setHeader("X-A2B-Source", "vite-dev-fallback");
        createReadStream(file).pipe(res);
      });
    },
  };
}

// Quest 3 over the LAN (`npm run dev:quest`): WebXR needs a secure origin, so serve a self-signed https://<laptop-ip>.
// With a USB cable, `adb reverse tcp:5173 tcp:5173` + http://localhost:5173 on the Quest works without a certificate.
const https = process.env.A2B_HTTPS === "1";

export default defineConfig({
  plugins: [derivedFiles(), ...(https ? [basicSsl({ name: "a2b-quest" })] : [])],
  build: {
    rollupOptions: {
      input: { main: resolve(here, "index.html"), capture: resolve(here, "capture.html") },
    },
  },
  server: {
    port: 5173,
    fs: { allow: [here, resolve(repoRoot, "design")] }, // style.css imports design/cyberpunk-tokens.css
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
