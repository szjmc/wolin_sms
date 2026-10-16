"use client";
// 前端登录态小工具：保存令牌、读当前用户、退出登录
import { api, setToken } from "@/lib/client";

export interface CurrentUser {
  id: number;
  username: string;
  display_name: string;
  role: string;
  class_id: number | null;
}

const USER_KEY = "wolin_user";

export function readUser(): CurrentUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CurrentUser;
  } catch {
    return null;
  }
}

export async function login(username: string, password: string): Promise<CurrentUser> {
  const data = await api<{ token: string; user: CurrentUser }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(data.token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  return data.user;
}

export async function register(input: {
  username: string;
  password: string;
  display_name: string;
  role: string;
  class_id?: number | null;
}): Promise<CurrentUser> {
  return api<CurrentUser>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(input) });
}

export async function logout() {
  try {
    await api("/api/v1/auth/logout", { method: "POST" });
  } catch {
    // 令牌已经失效也没关系，本地照样清掉
  }
  setToken(null);
  window.localStorage.removeItem(USER_KEY);
}

/** 角色中文名，页面展示用 */
export const ROLE_LABELS: Record<string, string> = {
  admin: "系统管理员",
  head_teacher: "班主任",
  teacher: "授课老师",
  employment: "就业专员",
  viewer: "只读用户",
};
