// Hoola App Engine - locked by Hoola (the build reads it; the app's own code cannot change it).
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import hoolaSource, { hoolaIslands } from "./hoola.plugin.mjs";
import { fileURLToPath, URL } from "node:url";

const VENDOR: [RegExp, string][] = [
  [/node_modules\/(react|react-dom|scheduler)\//, "react"],
  [/node_modules\/(react-router|react-router-dom|@remix-run)\//, "router"],
  [/node_modules\/@tanstack\//, "query"],
  [/node_modules\/sonner\//, "sonner"],
];
function vendor(id: string): string | undefined {
  const f = id.replace(/\\/g, "/");
  for (const [rx, name] of VENDOR) if (rx.test(f)) return name;
  return undefined;
}

const SOURCE_MAPS = process.env.HOOLA_SOURCE === "1" ? ("hidden" as const) : false;

// three builds (v0.999.64 D3), one config:
//   vite build                -> dist/        the whole app, exactly as before (one bundle)
//   vite build --mode islands -> dist/isl/    only what a pre-rendered site page's islands need (libraries split out)
//   vite build --ssr ...      -> dist-ssr/    the server render hoola.prerender.mjs uses (every package inside it)
export default defineConfig(({ isSsrBuild, mode }) => ({
  base: "./",
  cacheDir: "/tmp/vite-cache",
  plugins: [hoolaSource(), hoolaIslands(), react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  ssr: { noExternal: true, target: "node" },
  // a preview build keeps hidden source maps so an error in the preview names the app's own file and line
  build: isSsrBuild
    ? { outDir: "dist-ssr", emptyOutDir: true, sourcemap: false, minify: false, copyPublicDir: false }
    : mode === "islands"
      ? { outDir: "dist/isl", emptyOutDir: true, sourcemap: SOURCE_MAPS, copyPublicDir: false, manifest: true,
          chunkSizeWarningLimit: 1500,
          rollupOptions: { input: { islands: fileURLToPath(new URL("./src/islands-entry.tsx", import.meta.url)) },
                           output: { manualChunks: vendor, entryFileNames: "[name]-[hash].js",
                                     chunkFileNames: "[name]-[hash].js", assetFileNames: "[name]-[hash][extname]" } } }
      : { outDir: "dist", emptyOutDir: true, sourcemap: SOURCE_MAPS, assetsInlineLimit: 4096, chunkSizeWarningLimit: 1500 },
}));
