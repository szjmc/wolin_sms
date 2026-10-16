import { defineConfig } from "@playwright/test";

// 只连接平台已经启动的预览，不额外创建长期 next dev/start 进程。
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 45000,
  workers: 1,
  reporter: "list",
  outputDir: "/tmp/wolin-browser-artifacts",
  use: {
    baseURL: process.env.WOLIN_E2E_BASE_URL || "http://127.0.0.1:3000",
    browserName: "chromium",
    headless: true,
    trace: "off",
    screenshot: "only-on-failure",
  },
});
