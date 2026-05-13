import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://web:8000",
        changeOrigin: true,
      },
    },
    // Allow `?raw` imports from the repo's top-level docs/ folder (HELP/FAQ
    // markdown) in dev mode. The production build doesn't need this.
    fs: { allow: [".."] },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // Heavy 2D canvas lib — keeps the main bundle small for users
          // who never open the editor.
          konva: ["konva", "react-konva", "use-image"],
          // Stable shared deps that change rarely → long-term browser cache.
          react: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});
