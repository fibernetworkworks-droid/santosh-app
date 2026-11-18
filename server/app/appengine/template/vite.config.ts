// Hoola App Engine - locked by Hoola (the build reads it; the app's own code cannot change it).
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import hoolaSource from "./hoola.plugin.mjs";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  base: "./",
  cacheDir: "/tmp/vite-cache",
  plugins: [hoolaSource(), react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  // a preview build keeps hidden source maps so an error in the preview names the app's own file and line
  build: { outDir: "dist", emptyOutDir: true, sourcemap: process.env.HOOLA_SOURCE === "1" ? "hidden" : false, assetsInlineLimit: 4096, chunkSizeWarningLimit: 1500 },
});
