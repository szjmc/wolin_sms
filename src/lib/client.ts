"use client";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("wolin_token");
}
export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem("wolin_token", token);
  else window.localStorage.removeItem("wolin_token");
}

/** 失效令牌和旧用户资料一起清理，避免登录页与工作台相互重定向。 */
export function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("wolin_token");
  window.localStorage.removeItem("wolin_user");
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const token = getToken();
  const response = await fetch(path, {
    ...init,
    cache: "no-store",
    headers: { ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(init?.headers ?? {}) },
  });
  if (response.status === 204) return undefined as T;
  if (response.status === 401 && token && getToken() === token) {
    // 旧请求不能清掉后来登录的新令牌，因此必须先比较令牌是否仍相同。
    clearSession();
    window.dispatchEvent(new Event("wolin:session-expired"));
  }
  let body: { code: number; message: string; data: T; details?: { field?: string; reason: string }[] };
  try { body = await response.json(); }
  catch { throw new ApiError(response.status, "服务暂时不可用，请稍后重试"); }
  if (!response.ok || body.code !== 0) {
    const details = body.details?.slice(0, 8).map((item) => `${item.field ?? ""} ${item.reason}`).join("；");
    throw new ApiError(response.status, `${body.message || "请求失败"}${details ? `：${details}` : ""}`);
  }
  return body.data;
}
export type PageResult<T> = { items: T[]; total: number; page: number; page_size: number };
