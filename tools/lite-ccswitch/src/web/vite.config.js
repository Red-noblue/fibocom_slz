/**
 * Lite CC Switch React 管理台构建配置。
 * 将服务器版 Web 管理台构建到 ../public，继续由现有 Node 服务托管。
 */
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: path.resolve(process.cwd(), "web"),
  base: "/",
  plugins: [react()],
  build: {
    outDir: path.resolve(process.cwd(), "public"),
    emptyOutDir: true,
  },
  server: {
    host: "0.0.0.0",
    port: 15723,
    proxy: {
      "/api": "http://127.0.0.1:15721",
      "/v1": "http://127.0.0.1:15721",
    },
  },
});
