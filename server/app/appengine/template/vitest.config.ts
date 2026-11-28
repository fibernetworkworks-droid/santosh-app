// Hoola App Engine - locked by Hoola. The app's tests (src/**/*.test.ts / .tsx) run in the box: app_engine action=test.
// Write tests with Vitest + React Testing Library:
//   import { describe, it, expect } from "vitest";
//   import { render, screen } from "@testing-library/react";
//   import userEvent from "@testing-library/user-event";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  cacheDir: "/tmp/vite-cache",
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./vitest.setup.ts"],
    css: false,
    testTimeout: 10000,
    pool: "threads",
    maxWorkers: 2,
    restoreMocks: true,
    // no test may reach the network (the box has none); fake timers and mocks are the test's own
  },
});
