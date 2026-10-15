/** 统一成功 / 失败响应，字段与 FastAPI 后端契约一致。 */

export function jsonOk(data: unknown, status = 200) {
  return Response.json({ code: 0, message: "success", data }, { status });
}

export function jsonErr(httpStatus: number, message: string, details: { field?: string; reason: string }[] = []) {
  return Response.json({ code: httpStatus * 100 + 1, message, details }, { status: httpStatus });
}

export function json204() {
  return new Response(null, { status: 204 });
}

export function pageData<T>(items: T[], total: number, page: number, pageSize: number) {
  return { items, total, page, page_size: pageSize };
}

export function readPage(url: URL) {
  const page = Math.max(1, Number(url.searchParams.get("page") || 1));
  let pageSize = Number(url.searchParams.get("page_size") || 20);
  if (!Number.isFinite(pageSize) || pageSize < 1) pageSize = 20;
  if (pageSize > 100) pageSize = 100;
  return { page, pageSize };
}

export async function readJson(request: Request): Promise<Record<string, unknown> | null> {
  try {
    const body = await request.json();
    if (typeof body !== "object" || body === null || Array.isArray(body)) return null;
    return body as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function asString(value: unknown): string | undefined {
  return typeof value === "string" ? value.trim() : undefined;
}

export function asNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) return Number(value);
  return undefined;
}

export function money(value: unknown): string {
  const n = Number(value ?? 0);
  return n.toFixed(2);
}
