import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://127.0.0.1:4173" },
  webServer: {
    command: "bun run build && bunx vite preview --host 127.0.0.1",
    port: 4173,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
