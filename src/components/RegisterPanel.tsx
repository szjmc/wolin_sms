"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, useEffect } from "react";
import { ArrowLeft, ArrowRight, KeyRound, LogIn, UserPlus } from "lucide-react";
import { api } from "@/lib/client";
import { getToken } from "@/lib/client";
import { login, register } from "@/lib/auth-client";
import { Button, ErrorText, Field, inputClass, SuccessText } from "@/components/ui";

/**
 * 用户自助注册页：无论系统是否已初始化，访客都可以注册一个只读账号。
 * 管理员（admin/admin123）账号与教师类角色账号仍由管理员在用户管理中创建，防止越权。
 */
export function RegisterPanel() {
  const router = useRouter();
  const [form, setForm] = useState({ username: "", password: "", confirm: "", display_name: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [manager, setManager] = useState(false);
  const change = (key: keyof typeof form, value: string) => setForm((old) => ({ ...old, [key]: value }));

  // 已登录的管理者进来时，提示直接去用户管理建号，这里只服务普通访客。
  useEffect(() => {
    if (!getToken()) return;
    void api<{ role: string }>("/api/v1/auth/me").then((user) => {
      if (["admin", "head_teacher"].includes(user.role)) setManager(true);
    }).catch(() => undefined);
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (form.password !== form.confirm) { setError("两次输入的密码不一致"); return; }
    setBusy(true); setError(null); setMessage(null);
    try {
      // 访客自助注册固定为只读角色，不接受客户端指定角色。
      await register({ username: form.username.trim(), password: form.password, display_name: form.display_name.trim(), role: "viewer", class_id: null });
      // 注册成功后自动登录，直接进入工作台（只读视图）。
      await login(form.username.trim(), form.password);
      router.replace("/dashboard");
    } catch (e) { setError(e instanceof Error ? e.message : "注册失败，请重试"); }
    finally { setBusy(false); }
  }

  return <main className="login-scene min-h-screen"><div className="mx-auto flex min-h-screen max-w-xl items-center px-5 py-10"><section className="w-full rounded-3xl border border-white/60 bg-white p-8 shadow-2xl shadow-indigo-950/15 sm:p-10">
    <Link href="/" className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-indigo-600"><ArrowLeft size={13} />返回登录</Link>
    <div className="mb-7 mt-7"><span className="grid h-11 w-11 place-items-center rounded-xl bg-indigo-50 text-indigo-600"><UserPlus size={20} /></span><h1 className="mt-5 text-2xl font-bold text-slate-900">用户注册</h1><p className="mt-2 text-sm leading-6 text-slate-500">填写账号资料即可注册，注册后自动登录。</p></div>
    <ErrorText error={error} /><SuccessText message={message} />
    {manager ? <div className="mb-5 space-y-4 rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm leading-7 text-amber-700"><p>你已登录管理账号。新建教师或管理角色账号请前往「用户管理」，可指定角色与所属班级。</p><Link href="/users" className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white">进入用户管理<ArrowRight size={14} /></Link></div> : null}
    <form onSubmit={submit} className="space-y-4">
      <Field label="登录账号"><input className={inputClass} required minLength={3} maxLength={50} autoComplete="username" placeholder="3-50 个字符" value={form.username} onChange={(e) => change("username", e.target.value)} /></Field>
      <Field label="显示名称"><input className={inputClass} required maxLength={50} placeholder="请输入姓名或昵称" value={form.display_name} onChange={(e) => change("display_name", e.target.value)} /></Field>
      <Field label="密码"><input className={inputClass} required type="password" minLength={6} maxLength={72} autoComplete="new-password" placeholder="至少 6 位" value={form.password} onChange={(e) => change("password", e.target.value)} /></Field>
      <Field label="确认密码"><input className={inputClass} required type="password" minLength={6} maxLength={72} autoComplete="new-password" placeholder="再输入一次密码" value={form.confirm} onChange={(e) => change("confirm", e.target.value)} /></Field>
      <Button type="submit" disabled={busy} className="mt-2 w-full !py-3"><KeyRound size={15} />{busy ? "正在注册…" : "注册并登录"}</Button>
    </form>
    <div className="mt-6 space-y-2 border-t border-slate-100 pt-5 text-[11px] leading-6 text-slate-400">
      <p>· 自助注册的账号为「只读用户」，可查看学生、班级、成绩、就业与统计。</p>
      <p>· 班主任、授课老师、就业专员、管理员账号由管理员在「用户管理」中创建。</p>
      <p className="flex items-center gap-1"><LogIn size={12} />已有账号？<Link href="/" className="text-indigo-600">直接登录</Link></p>
    </div>
  </section></div></main>;
}
