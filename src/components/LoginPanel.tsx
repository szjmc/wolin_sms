"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { GraduationCap, KeyRound, LogIn, ShieldCheck } from "lucide-react";
import { login, type CurrentUser } from "@/lib/auth-client";
import { api, ApiError, clearSession, getToken } from "@/lib/client";
import { Button, ErrorText, Field, inputClass } from "@/components/ui";

/** 独立登录页面：不公开任何管理员账号或默认密码。 */
export function LoginPanel() {
  const router = useRouter();
  const [username, setUsername] = useState(""); const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false); const [help, setHelp] = useState(false);
  const [initialized, setInitialized] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (getToken()) {
      setChecking(true);
      // 不能只判断 localStorage 有字符串，必须通过服务器验证。
      void api<CurrentUser>("/api/v1/auth/me").then((user) => {
        if (cancelled) return;
        window.localStorage.setItem("wolin_user", JSON.stringify(user));
        router.replace("/dashboard");
      }).catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
          clearSession(); setError("之前的登录已失效，请使用当前账号和密码重新登录。");
        } else {
          setError("暂时无法验证登录状态，请检查服务后重试，或直接重新登录。");
        }
      }).finally(() => { if (!cancelled) setChecking(false); });
    }
    return () => { cancelled = true; };
  }, [router]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null); setBusy(true);
    try {
      // 手动登录时清除旧缓存，不携带过期身份信息。
      clearSession();
      await login(username.trim(), password);
      router.replace("/dashboard");
    } catch (e) { setError(e instanceof Error ? e.message : "登录失败，请重试"); }
    finally { setBusy(false); }
  }

  return <main className="login-scene min-h-screen">
    <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-10 px-5 py-10 lg:grid-cols-[1.1fr_0.9fr] lg:px-10">
      <section className="hidden text-white lg:block"><div className="mb-8 grid h-14 w-14 place-items-center rounded-2xl bg-white/15 ring-1 ring-white/25"><GraduationCap size={30} /></div><p className="text-xs font-semibold uppercase tracking-[.28em] text-indigo-200">WOLIN EDUCATION</p><h1 className="mt-4 text-4xl font-bold leading-tight">沃林学生管理系统</h1><p className="mt-4 max-w-lg text-sm leading-7 text-indigo-100">连接学生档案、教学考核与职业发展，让每个关键成长节点清晰可见。</p><div className="mt-10 flex items-center gap-2 text-xs text-indigo-100"><ShieldCheck size={16} />安全登录 · 统一管理 · 历史可追溯</div></section>
      <section className="mx-auto w-full max-w-md rounded-3xl border border-white/60 bg-white p-8 shadow-2xl shadow-indigo-950/15 sm:p-10">
        <div className="mb-8 flex items-center gap-3 lg:hidden"><span className="grid h-11 w-11 place-items-center rounded-xl bg-indigo-600 text-white"><GraduationCap size={24} /></span><span className="text-lg font-bold text-slate-900">沃林学生管理系统</span></div>
        <div className="mb-7"><span className="grid h-11 w-11 place-items-center rounded-xl bg-indigo-50 text-indigo-600"><KeyRound size={20} /></span><h2 className="mt-5 text-2xl font-bold text-slate-900">欢迎登录</h2><p className="mt-2 text-sm text-slate-500">请输入账号和密码进入工作空间</p></div>
        <ErrorText error={error} />
        <form onSubmit={submit} className="space-y-5">
          <Field label="登录账号"><input className={inputClass} autoComplete="username" required minLength={3} maxLength={50} value={username} onChange={(e) => setUsername(e.target.value)} placeholder="请输入登录账号" /></Field>
          <Field label="密码"><input className={inputClass} type="password" autoComplete="current-password" required minLength={6} maxLength={72} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="请输入密码" /></Field>
          <Button type="submit" disabled={busy || checking} className="mt-2 w-full !py-3"><LogIn size={16} />{checking ? "验证登录状态…" : busy ? "正在登录…" : "登录系统"}</Button>
        </form>
        <div className="mt-5 text-right"><button type="button" onClick={() => setHelp(!help)} aria-expanded={help} className="text-xs font-medium text-indigo-600">忘记管理员密码？</button></div>
        {help && <div role="note" className="mt-3 rounded-xl bg-slate-50 p-4 text-xs leading-6 text-slate-500">无需重新注册，也不需要清空数据。请由系统维护人员在部署终端运行管理员恢复工具，重置后使用新密码登录。若已收到临时密码，请直接在上方输入，登录后到「个人信息」修改密码。</div>}
        <div className="mt-6 border-t border-slate-100 pt-5 text-center text-xs leading-6 text-slate-500">还没有账号？<Link href="/register" className="ml-1 font-semibold text-indigo-600">注册新用户</Link><br /><span className="text-slate-400">自助注册为只读账号；教师与管理角色由管理员创建</span></div>
      </section>
    </div>
  </main>;
}
