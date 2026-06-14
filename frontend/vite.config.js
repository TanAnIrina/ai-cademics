import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During `npm run dev` the frontend talks to the backend on :8000 through a
// proxy, so the app can use same-origin "/api" calls everywhere. In production
// the built static files are served by nginx, which proxies /api to the
// backend container (see frontend/nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
