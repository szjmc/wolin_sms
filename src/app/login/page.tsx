import { redirect } from "next/navigation";

/** 旧登录路径统一返回根登录页，避免重复入口。 */
export default function LoginAliasPage() {
  redirect("/");
}
