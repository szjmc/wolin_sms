import "server-only";
import { handleWolin } from "@/lib/wolin-api";

/** 服务端页面与浏览器使用同一业务数据源，正式部署不另读预览数据库。 */
export async function serverApi<T>(path: string): Promise<T> {
  const backend = process.env.WOLIN_API_URL;
  const response = backend
    ? await fetch(`${backend.replace(/\/$/, "")}/api/v1/${path}`, { cache: "no-store", signal: AbortSignal.timeout(30000) })
    : await handleWolin("GET", path.split("?")[0].split("/"), new Request(`http://internal/api/v1/${path}`));
  const body = await response.json();
  if (!response.ok || body.code !== 0) throw new Error(body.message || "业务数据读取失败");
  return body.data as T;
}
