"use client";
import { api, type PageResult } from "@/lib/client";

/** 下拉选项按统一分页逐页获取，不把 100 条误当作全部数据。 */
export async function loadOptions<T>(path: string): Promise<T[]> {
  const result: T[] = [];
  let page = 1;
  while (true) {
    const separator = path.includes("?") ? "&" : "?";
    const data = await api<PageResult<T>>(`${path}${separator}page=${page}&page_size=100`);
    result.push(...data.items);
    if (result.length >= data.total || data.items.length === 0) break;
    page += 1;
  }
  return result;
}

export function queryString(values: Record<string, string | number | null | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== "" && value !== undefined && value !== null) query.set(key, String(value));
  }
  return query.toString();
}

export function displayMoney(value: string | number | null | undefined): string {
  if (value == null) return "—";
  return Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}
