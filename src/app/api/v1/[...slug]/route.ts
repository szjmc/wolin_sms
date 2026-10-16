import { handleWolin } from "@/lib/wolin-api";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
type Ctx = { params: Promise<{ slug: string[] }> };
async function run(method: string, request: Request, ctx: Ctx) {
  const { slug } = await ctx.params;
  // 正式部署配置 FastAPI 地址后，只代理到 Python/MySQL，不静默回退。
  const backend = process.env.WOLIN_API_URL;
  if (backend) {
    try {
      const url = new URL(request.url);
      const headers = new Headers();
      const contentType = request.headers.get("Content-Type");
      if (contentType) headers.set("Content-Type", contentType);
      // 必须转发令牌，否则 Python 登录成功后的 /auth/me 总是返回 401。
      const authorization = request.headers.get("Authorization");
      if (authorization) headers.set("Authorization", authorization);
      const upstream = await fetch(`${backend.replace(/\/$/, "")}/api/v1/${slug.map(encodeURIComponent).join("/")}${url.search}`, {
        method, headers, body: ["GET", "HEAD"].includes(method) ? undefined : await request.arrayBuffer(),
        cache: "no-store", signal: AbortSignal.timeout(60000),
      });
      const responseHeaders = new Headers();
      for (const name of ["Content-Type", "Content-Disposition"]) {
        const value = upstream.headers.get(name); if (value) responseHeaders.set(name, value);
      }
      return new Response(upstream.status === 204 ? null : upstream.body, { status: upstream.status, headers: responseHeaders });
    } catch {
      return Response.json({ code: 50301, message: "后端服务暂不可用，请检查 FastAPI 地址", details: [] }, { status: 503 });
    }
  }
  return handleWolin(method, slug ?? [], request);
}
export async function GET(request: Request, ctx: Ctx) { return run("GET", request, ctx); }
export async function POST(request: Request, ctx: Ctx) { return run("POST", request, ctx); }
export async function PATCH(request: Request, ctx: Ctx) { return run("PATCH", request, ctx); }
export async function PUT(request: Request, ctx: Ctx) { return run("PUT", request, ctx); }
export async function DELETE(request: Request, ctx: Ctx) { return run("DELETE", request, ctx); }
