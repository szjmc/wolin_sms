/**
 * 仅限有部署终端权限的维护人员执行，不提供任何公开 HTTP 重置接口。
 * 读取当前项目 .env 的 DATABASE_URL，所有读写都通过 Drizzle。
 * 不导入 bootstrap，避免重置账号时触碰任何业务表或演示数据。
 */
import "dotenv/config";
import { randomBytes } from "node:crypto";
import { asc, eq } from "drizzle-orm";
import { db, pool } from "@/db";
import { users } from "@/db/schema";
import { hashPassword, passwordError } from "@/lib/password";

async function main() {
  if (process.env.WOLIN_API_URL) {
    throw new Error("当前已对接 FastAPI，请在该服务的部署终端执行 python backend/reset_admin.py；拒绝重置错误的数据源。");
  }
  const args = process.argv.slice(2);
  const nameIndex = args.indexOf("--username");
  const username = nameIndex >= 0 ? args[nameIndex + 1]?.trim() : "admin";
  if (!username || username.length < 3 || username.length > 50) throw new Error("账号长度必须是 3–50 字符");
  if (args.includes("--list")) {
    const rows = await db.select({ id: users.id, username: users.username, display_name: users.displayName,
      is_active: users.isActive, is_deleted: users.isDeleted }).from(users)
      .where(eq(users.role, "admin")).orderBy(asc(users.id));
    console.table(rows);
    return;
  }
  const generated = args.includes("--generate");
  const password = generated ? `Wl!${randomBytes(12).toString("base64url")}` : process.env.WOLIN_ADMIN_PASSWORD;
  const invalid = passwordError(password);
  if (invalid) throw new Error(`${invalid}。请使用 --generate，或从 WOLIN_ADMIN_PASSWORD 环境变量传入。`);
  const passwordHash = await hashPassword(password!);
  const result = await db.transaction(async (tx) => {
    const [existing] = await tx.select().from(users).where(eq(users.username, username)).for("update");
    if (existing) {
      if (existing.role !== "admin") throw new Error("该账号不是管理员，拒绝自动提权；请选用管理员账号或新建专用管理员。");
      const [updated] = await tx.update(users).set({ passwordHash, token: null, isActive: 1, isDeleted: 0,
        deletedAt: null, updatedAt: new Date() }).where(eq(users.id, existing.id)).returning();
      return { username: updated.username, created: false };
    }
    if (!args.includes("--create-if-missing")) throw new Error("账号不存在。需要新建管理员时，请显式添加 --create-if-missing。");
    const [created] = await tx.insert(users).values({ username, passwordHash, displayName: "系统管理员",
      role: "admin", classId: null, token: null, isActive: 1 }).returning();
    return { username: created.username, created: true };
  });
  console.log(`${result.created ? "已创建" : "已恢复"}管理员：${result.username}`);
  if (generated) console.log(`临时密码（仅本次终端输出）：${password}`);
  console.log("账号已启用，旧令牌已撤销。未更改任何学生、班级、成绩、就业数据。请登录后在个人信息中修改密码。");
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : "管理员恢复失败");
  process.exitCode = 1;
}).finally(async () => { await pool.end(); });
