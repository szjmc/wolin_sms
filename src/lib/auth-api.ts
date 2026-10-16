/**
 * 登录注册与权限（预览环境的实现）
 * ==================================
 * Python 后端 backend/api/auth_api.py 是正式实现（bcrypt 加密）；
 * 预览同样使用 bcrypt；旧 scrypt 密码验证成功后自动升级，不要求用户先改密码。
 *
 * 账号规则：
 * 1. 系统第一个账号自动成为管理员，之后通过用户管理建号
 * 2. 密码只存 bcrypt 加密结果，接口永远不返回密码
 * 3. 角色分工：管理员全权 / 班主任只管自己班 / 授课老师只管自己班成绩 /
 *    就业专员管就业 / 只读只能看
 */
import { randomBytes } from "node:crypto";
import { hashPassword, passwordError, verifyPassword } from "@/lib/password";
import { and, count, eq, like } from "drizzle-orm";
import { db } from "@/db";
import { classes, employmentRecords, scores, students, users } from "@/db/schema";
import { asString, jsonErr, jsonOk, pageData, readJson, readPage } from "@/lib/http";

export type UserRole = "admin" | "head_teacher" | "teacher" | "employment" | "viewer";
export interface AuthUser {
  id: number;
  username: string;
  display_name: string;
  role: UserRole;
  class_id: number | null;
}

// 每个角色能操作的模块；"*" 表示全部。setup = 班级建档/老师建档/账号管理
const ROLE_RULES: Record<string, string[]> = {
  admin: ["*"],
  // 班主任可管理普通账号，但不能通过账号管理获得管理员权限。
  head_teacher: ["student", "score", "employment", "class", "user"],
  teacher: ["score"],
  employment: ["employment"],
  viewer: [],
};
const CROSS_CLASS_ROLES = ["admin", "employment"];

function userView(row: typeof users.$inferSelect | undefined) {
  if (!row) throw jsonErr(404, "用户不存在或已删除");
  return {
    id: row.id, username: row.username, display_name: row.displayName,
    role: row.role as UserRole, class_id: row.classId, is_active: row.isActive === 1,
    created_at: row.createdAt, updated_at: row.updatedAt,
  };
}

/** 从 Authorization 头取当前登录用户；没登录/令牌失效直接抛 401 响应 */
export async function requireUser(request: Request): Promise<AuthUser> {
  const header = request.headers.get("authorization");
  if (!header) throw jsonErr(401, "请先登录");
  const match = /^Bearer\s+([a-f0-9]{48})$/i.exec(header);
  if (!match) throw jsonErr(401, "登录已失效，请重新登录");
  const token = match[1];
  const [row] = await db.select().from(users).where(and(eq(users.token, token), eq(users.isDeleted, 0), eq(users.isActive, 1))).limit(1);
  if (!row) throw jsonErr(401, "登录已失效，请重新登录");
  return { id: row.id, username: row.username, display_name: row.displayName, role: row.role as UserRole, class_id: row.classId };
}

export function checkPermission(user: AuthUser, module: string, classId?: number | null) {
  const allowed = ROLE_RULES[user.role] ?? [];
  if (!allowed.includes("*") && !allowed.includes(module)) throw jsonErr(403, `当前角色（${user.role}）无权操作该功能`);
  if (classId === undefined || classId === null) return;
  if (CROSS_CLASS_ROLES.includes(user.role)) return;
  if (user.class_id !== classId) throw jsonErr(403, "只能操作自己负责班级的数据");
}

/** 写操作前的统一权限闸门：返回 Response 表示拦截，null 表示放行 */
export async function guardWrite(method: string, path: string, request: Request): Promise<Response | null> {
  if (["POST", "PUT", "PATCH", "DELETE"].indexOf(method) < 0) return null;
  if (path.startsWith("auth/") || path === "auth" || path.startsWith("users")) return null;
  let user: AuthUser;
  try { user = await requireUser(request); } catch (error) { return error as Response; }

  const head = path.split("/")[0];
  const moduleMap: Record<string, string> = {
    students: "student", "past-experiences": "student", scores: "score",
    "employment-records": "employment", classes: "class", "class-teacher-relations": "class",
    teachers: "setup",
  };
  const module = moduleMap[head];
  if (!module) return null;

  // 能顺手拿到班级的就按班级拦，拿不到的只做模块级校验（正式实现以 Python 为准）
  let classId: number | null = null;
  const body = ["POST", "PATCH", "PUT"].includes(method) ? await request.clone().json().catch(() => null) : null;
  if (head === "students" && body && typeof body.class_id === "number") classId = body.class_id;
  if (head === "scores" && body && typeof body.student_id === "number") {
    const [s] = await db.select({ classId: students.classId }).from(students).where(eq(students.id, body.student_id)).limit(1);
    classId = s?.classId ?? null;
  }
  if (head === "employment-records" && body && typeof body.student_id === "number") {
    const [s] = await db.select({ classId: students.classId }).from(students).where(eq(students.id, body.student_id)).limit(1);
    classId = s?.classId ?? null;
  }
  if (head === "students" && path.split("/").length === 2) {
    const [s] = await db.select({ classId: students.classId }).from(students).where(eq(students.id, Number(path.split("/")[1]))).limit(1);
    classId = s?.classId ?? null;
  }
  try {
    checkPermission(user, module, classId);
    return null;
  } catch (error) {
    return error as Response;
  }
}

/** 登录注册接口（与 Python 后端路径、响应完全一致） */
export async function handleAuth(method: string, slug: string[], request: Request): Promise<Response | null> {
  const path = slug.join("/");

  // 只返回初始化标记，不公开账号名称、密码或用户列表。
  if (path === "auth/status" && method === "GET") {
    const [{ total }] = await db.select({ total: count() }).from(users);
    return jsonOk({ initialized: Number(total) > 0 });
  }

  if (path === "auth/register" && method === "POST") {
    const body = await readJson(request);
    if (!body) return jsonErr(422, "请求体必须是 JSON");
    const username = asString(body.username);
    const password = typeof body.password === "string" ? body.password : "";
    const displayName = asString(body.display_name);
    const role = asString(body.role) || "viewer";
    if (!username || username.length < 3 || username.length > 50) return jsonErr(422, "用户名必须是 3-50 个字符");
    if (passwordError(password)) return jsonErr(422, passwordError(password)!);
    if (!displayName) return jsonErr(422, "显示名称不能为空");
    if (!["admin", "head_teacher", "teacher", "employment", "viewer"].includes(role)) return jsonErr(422, "角色不合法");
    const [exist] = await db.select({ id: users.id }).from(users).where(eq(users.username, username)).limit(1);
    if (exist) return jsonErr(409, "用户名已存在");
    const [{ total }] = await db.select({ total: count() }).from(users);
    let finalRole = role as UserRole;
    let classId = typeof body.class_id === "number" ? body.class_id : null;

    if (Number(total) === 0) {
      // 系统一个账号都没有：第一个注册的账号自动成为管理员
      finalRole = "admin"; classId = null;
    } else {
      // 系统已有账号：先看请求是不是来自已登录的管理者（带令牌）
      let manager = null;
      if (request.headers.get("authorization")) {
        try { manager = await requireUser(request); } catch { manager = null; }
      }
      if (manager !== null && (manager.role === "admin" || manager.role === "head_teacher")) {
        // 管理员/班主任建号：按请求里的角色创建，班主任不能建管理员
        if (manager.role !== "admin" && role === "admin") return jsonErr(403, "只有管理员可以创建管理员账号");
      } else {
        // 普通访客自助注册：只允许只读账号，防止匿名创建越权账号
        if (role !== "viewer") return jsonErr(403, "班主任、授课老师、就业专员和管理员账号需由管理员创建；访客可先注册只读账号");
        finalRole = "viewer"; classId = null;
      }
    }
    if ((finalRole === "head_teacher" || finalRole === "teacher") && !classId) return jsonErr(422, "班主任和授课老师必须填写所属班级 class_id");
    if (classId !== null) {
      const [cls] = await db.select({ id: classes.id }).from(classes).where(and(eq(classes.id, classId), eq(classes.isDeleted, 0))).limit(1);
      if (!cls) return jsonErr(404, "班级不存在或已删除");
    }
    const [row] = await db.insert(users).values({
      username, passwordHash: await hashPassword(password), displayName,
      role: finalRole, classId, isActive: 1,
    }).returning();
    return jsonOk(userView(row), 201);
  }

  if (path === "auth/login" && method === "POST") {
    const body = await readJson(request);
    if (!body) return jsonErr(422, "请求体必须是 JSON");
    const [row] = await db.select().from(users).where(and(eq(users.username, asString(body.username) ?? ""), eq(users.isDeleted, 0))).limit(1);
    if (!row || !(await verifyPassword(String(body.password ?? ""), row.passwordHash))) return jsonErr(400, "用户名或密码错误");
    if (row.isActive !== 1) return jsonErr(403, "账号已被停用，请联系管理员");
    const token = randomBytes(24).toString("hex");
    // 只有密码验证成功后才迁移旧哈希，迁移失败不会绕过认证。
    const passwordHash = row.passwordHash.startsWith("$2") ? row.passwordHash : await hashPassword(String(body.password));
    const [updated] = await db.update(users).set({ token, passwordHash, updatedAt: new Date() }).where(eq(users.id, row.id)).returning();
    return jsonOk({ token, user: userView(updated) });
  }

  if (path === "auth/logout" && method === "POST") {
    try {
      const user = await requireUser(request);
      await db.update(users).set({ token: null, updatedAt: new Date() }).where(eq(users.id, user.id));
      return jsonOk(null);
    } catch (error) {
      return error as Response;
    }
  }

  if (path === "auth/me" && method === "GET") {
    try {
      const user = await requireUser(request);
      const [row] = await db.select().from(users).where(eq(users.id, user.id)).limit(1);
      return jsonOk(userView(row));
    } catch (error) {
      return error as Response;
    }
  }

  if (path === "auth/change-password" && method === "POST") {
    try {
      const current = await requireUser(request);
      const body = await readJson(request);
      if (!body) return jsonErr(422, "请求体必须是 JSON");
      const oldPassword = typeof body.current_password === "string" ? body.current_password : "";
      const newPassword = typeof body.new_password === "string" ? body.new_password : "";
      if (!(await verifyPassword(oldPassword, (await db.select().from(users).where(eq(users.id, current.id)).limit(1))[0]?.passwordHash ?? ""))) return jsonErr(400, "当前密码不正确");
      if (passwordError(newPassword)) return jsonErr(422, passwordError(newPassword)!);
      await db.update(users).set({ passwordHash: await hashPassword(newPassword), token: null, updatedAt: new Date() }).where(eq(users.id, current.id));
      return jsonOk(null);
    } catch (error) {
      return error as Response;
    }
  }

  if (path === "users" && method === "GET") {
    try { checkPermission(await requireUser(request), "user"); }
    catch (error) { return error as Response; }
    const url = new URL(request.url);
    const { page, pageSize } = readPage(url);
    const filters = [eq(users.isDeleted, 0)];
    const username = url.searchParams.get("username");
    const role = url.searchParams.get("role");
    if (username) filters.push(like(users.username, `%${username}%`));
    if (role) filters.push(eq(users.role, role));
    const [{ total }] = await db.select({ total: count() }).from(users).where(and(...filters));
    const rows = await db.select().from(users).where(and(...filters)).orderBy(users.id).limit(pageSize).offset((page - 1) * pageSize);
    return jsonOk(pageData(rows.map(userView), Number(total), page, pageSize));
  }

  // 管理员与班主任可以新建普通账号；班主任不能创建 admin。
  if (path === "users" && method === "POST") {
    let current: AuthUser;
    try { current = await requireUser(request); checkPermission(current, "user"); }
    catch (error) { return error as Response; }
    const body = await readJson(request);
    if (!body) return jsonErr(422, "请求体必须是 JSON");
    const username = asString(body.username);
    const password = typeof body.password === "string" ? body.password : "";
    const displayName = asString(body.display_name);
    const role = asString(body.role) || "viewer";
    if (!username || username.length < 3 || username.length > 50) return jsonErr(422, "用户名必须是 3-50 个字符");
    if (passwordError(password)) return jsonErr(422, passwordError(password)!);
    if (!displayName) return jsonErr(422, "显示名称不能为空");
    if (!["admin", "head_teacher", "teacher", "employment", "viewer"].includes(role)) return jsonErr(422, "角色不合法");
    if (current.role !== "admin" && role === "admin") return jsonErr(403, "班主任不能创建管理员账号");
    const [exists] = await db.select({ id: users.id }).from(users).where(eq(users.username, username)).limit(1);
    if (exists) return jsonErr(409, "用户名已存在");
    const classId = typeof body.class_id === "number" ? body.class_id : null;
    if (["head_teacher", "teacher"].includes(role) && classId === null) return jsonErr(422, "班主任和授课老师必须绑定所属班级");
    if (classId !== null) {
      const [cls] = await db.select({ id: classes.id }).from(classes).where(and(eq(classes.id, classId), eq(classes.isDeleted, 0))).limit(1);
      if (!cls) return jsonErr(404, "班级不存在或已删除");
    }
    const [row] = await db.insert(users).values({ username, passwordHash: await hashPassword(password), displayName, role, classId, isActive: 1 }).returning();
    return jsonOk(userView(row), 201);
  }

  if (slug[0] === "users" && slug.length === 2 && /^\d+$/.test(slug[1])) {
    let current: AuthUser;
    try { current = await requireUser(request); checkPermission(current, "user"); }
    catch (error) { return error as Response; }
    const id = Number(slug[1]);
    const [row] = await db.select().from(users).where(and(eq(users.id, id), eq(users.isDeleted, 0))).limit(1);
    if (!row) return jsonErr(404, "用户不存在或已删除");
    if (method === "GET") return jsonOk(userView(row));
    if (current.role !== "admin" && row.role === "admin") return jsonErr(403, "班主任不能修改管理员账号");
    if (method === "PATCH") {
      const body = await readJson(request);
      if (!body) return jsonErr(422, "请求体必须是 JSON");
      const patch: Partial<typeof users.$inferInsert> = { updatedAt: new Date() };
      if ("display_name" in body) {
        const name = asString(body.display_name);
        if (!name) return jsonErr(422, "显示名称不能为空");
        patch.displayName = name;
      }
      if ("password" in body) {
        const password = typeof body.password === "string" ? body.password : "";
        if (passwordError(password)) return jsonErr(422, passwordError(password)!);
        patch.passwordHash = await hashPassword(password);
        patch.token = null;
      }
      if ("role" in body) {
        const role = asString(body.role) || "";
        if (!["admin", "head_teacher", "teacher", "employment", "viewer"].includes(role)) return jsonErr(422, "角色不合法");
        if (current.role !== "admin" && role === "admin") return jsonErr(403, "班主任不能授予管理员角色");
        patch.role = role;
      }
      const newRole = patch.role ?? row.role;
      if ("class_id" in body) patch.classId = body.class_id == null || body.class_id === "" ? null : Number(body.class_id);
      const newClassId = patch.classId !== undefined ? patch.classId : row.classId;
      if (["head_teacher", "teacher"].includes(newRole) && newClassId == null) return jsonErr(422, "班主任和授课老师必须绑定所属班级");
      if (newClassId != null) {
        const [cls] = await db.select({ id: classes.id }).from(classes).where(and(eq(classes.id, newClassId), eq(classes.isDeleted, 0))).limit(1);
        if (!cls) return jsonErr(404, "班级不存在或已删除");
      }
      if ("is_active" in body) {
        patch.isActive = body.is_active ? 1 : 0;
        if (!patch.isActive) patch.token = null;
      }
      const [updated] = await db.update(users).set(patch).where(eq(users.id, id)).returning();
      return jsonOk(userView(updated));
    }
    if (method === "DELETE") {
      if (id === current.id) return jsonErr(409, "不能删除当前登录账号");
      await db.update(users).set({ isDeleted: 1, deletedAt: new Date(), token: null, updatedAt: new Date() }).where(eq(users.id, id));
      return new Response(null, { status: 204 });
    }
  }

  return null;
}

