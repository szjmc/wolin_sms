"use client";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(path, {
    ...init,
    headers: { ...(isForm ? {} : { "Content-Type": "application/json" }), ...(init?.headers ?? {}) },
  });
  if (response.status === 204) return undefined as T;
  const body = (await response.json()) as { code: number; message: string; data: T; details?: { field?: string; reason: string }[] };
  if (!response.ok || body.code !== 0) {
    const details = body.details?.slice(0, 8).map((item) => `${item.field ?? ""} ${item.reason}`).join("；");
    throw new ApiError(response.status, `${body.message || "请求失败"}${details ? `：${details}` : ""}`);
  }
  return body.data;
}

export type PageResult<T> = { items: T[]; total: number; page: number; page_size: number };
