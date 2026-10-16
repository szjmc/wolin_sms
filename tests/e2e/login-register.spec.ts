import { test, expect } from "@playwright/test";

test("默认管理员 admin/admin123 可登录并进入工作台", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "欢迎登录" })).toBeVisible();
  await page.getByLabel("登录账号", { exact: true }).fill("admin");
  await page.getByLabel("密码", { exact: true }).fill("admin123");
  await page.getByRole("button", { name: "登录系统", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "教务工作台" })).toBeVisible();
  await expect(page.getByText("系统管理员", { exact: false }).first()).toBeVisible();
});

test("登录页提供用户注册入口", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "注册新用户", exact: true }).click();
  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByRole("heading", { name: "用户注册" })).toBeVisible();
  await expect(page.getByLabel("登录账号", { exact: true })).toBeVisible();
});

test("普通用户自助注册后自动进入工作台", async ({ page }) => {
  const username = "e2e_" + Date.now().toString(36);
  await page.goto("/register");
  await page.getByLabel("登录账号", { exact: true }).fill(username);
  await page.getByLabel("显示名称", { exact: true }).fill("端到端用户");
  await page.getByLabel("密码", { exact: true }).fill("e2e-password-123");
  await page.getByLabel("确认密码", { exact: true }).fill("e2e-password-123");
  await page.getByRole("button", { name: "注册并登录", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "教务工作台" })).toBeVisible();
  // 只读账号不应看到用户管理入口
  await expect(page.getByRole("link", { name: "用户管理", exact: true })).toHaveCount(0);
});

test("失效缓存令牌被清除并停留在登录页", async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("stale-e2e")) {
      localStorage.setItem("wolin_token", "9".repeat(48));
      localStorage.setItem("wolin_user", JSON.stringify({ display_name: "旧缓存", role: "admin" }));
      sessionStorage.setItem("stale-e2e", "1");
    }
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "欢迎登录" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => localStorage.getItem("wolin_token"))).toBeNull();
  expect(new URL(page.url()).pathname).toBe("/");
});
