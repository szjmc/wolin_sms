import { test, expect } from "@playwright/test";

// 凭据由执行测试的部署人员通过环境变量提供，禁止写入源码。
const username = process.env.WOLIN_E2E_ADMIN_USERNAME;
const password = process.env.WOLIN_E2E_ADMIN_PASSWORD;

test("过期缓存令牌清除后停留在登录页，不发生循环跳转", async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("stale-session-test")) {
      localStorage.setItem("wolin_token", "0".repeat(48));
      localStorage.setItem("wolin_user", JSON.stringify({ display_name: "旧缓存", role: "admin" }));
      sessionStorage.setItem("stale-session-test", "1");
    }
  });
  let redirects = 0;
  page.on("request", (r) => { if (new URL(r.url()).pathname === "/dashboard") redirects += 1; });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "欢迎登录" })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "登录已失效" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => localStorage.getItem("wolin_token"))).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem("wolin_user"))).toBeNull();
  expect(new URL(page.url()).pathname).toBe("/");
  expect(redirects).toBe(0);
});

test("注册页对访客开放，只读账号可自助注册并进入系统", async ({ page }) => {
  const username = "guest_" + Date.now().toString(36);
  await page.goto("/register");
  await expect(page.getByRole("heading", { name: "用户注册" })).toBeVisible();
  await page.getByLabel("登录账号", { exact: true }).fill(username);
  await page.getByLabel("显示名称", { exact: true }).fill("浏览器访客");
  await page.getByLabel("密码", { exact: true }).fill("guest-password-123");
  await page.getByLabel("确认密码", { exact: true }).fill("guest-password-123");
  await page.getByRole("button", { name: "注册并登录", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "教务工作台" })).toBeVisible();
  // 访客注册的是只读账号，侧栏不应出现用户管理等管理入口
  await expect(page.getByRole("link", { name: "用户管理", exact: true })).toHaveCount(0);
});

test("服务故障显示重试信息，不把错误当登录成功或循环重定向", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("wolin_token", "1".repeat(48)));
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({
    status: 503, contentType: "application/json", body: JSON.stringify({ code: 50301, message: "临时服务故障", details: [] }),
  }));
  await page.goto("/");
  await expect(page.getByRole("alert").filter({ hasText: "暂时无法验证登录状态" })).toBeVisible();
  expect(new URL(page.url()).pathname).toBe("/");
  expect(await page.evaluate(() => localStorage.getItem("wolin_token"))).not.toBeNull();
});

test("恢复后的管理员可以登录、访问个人信息和退出", async ({ page }) => {
  test.skip(!username || !password, "需设置本次恢复的管理员测试凭据");
  await page.goto("/");
  await page.getByLabel("登录账号", { exact: true }).fill(username!);
  await page.getByLabel("密码", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "登录系统", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "教务工作台" })).toBeVisible();
  await page.getByRole("button", { name: /系统管理员/ }).click();
  await page.getByRole("link", { name: "个人信息", exact: true }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByRole("heading", { name: "个人信息", exact: true })).toBeVisible();
  await expect(page.getByText(`账号 ${username}`, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /系统管理员/ }).click();
  await page.getByRole("button", { name: "退出登录", exact: true }).click();
  await expect(page.getByRole("heading", { name: "欢迎登录" })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("wolin_token"))).toBeNull();
});


test("直接访问工作台时清除失效令牌并返回登录页", async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("stale-protected-page")) {
      localStorage.setItem("wolin_token", "2".repeat(48));
      sessionStorage.setItem("stale-protected-page", "1");
    }
  });
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "欢迎登录" })).toBeVisible();
  expect(new URL(page.url()).pathname).toBe("/");
  expect(await page.evaluate(() => localStorage.getItem("wolin_token"))).toBeNull();
});
