// Hoola App Engine - locked by Hoola (the build reads it; the app's own code cannot change it).
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  base: "./",
  cacheDir: "/tmp/vite-cache",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false, assetsInlineLimit: 4096, chunkSizeWarningLimit: 1500 },
});
