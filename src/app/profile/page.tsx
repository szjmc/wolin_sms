"use client";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, KeyRound, ShieldCheck, UserRound } from "lucide-react";
import { api, setToken } from "@/lib/client";
import { ROLE_LABELS } from "@/lib/auth-client";
import type { ClassItem } from "@/lib/contracts";
import { loadOptions } from "@/lib/options";
import { Badge, Button, ErrorText, Field, inputClass, PageHeader, SuccessText } from "@/components/ui";

interface Profile {
  id: number; username: string; display_name: string; role: string;
  class_id: number | null; is_active: boolean; created_at: string; updated_at: string;
}
export default function ProfilePage() {
  const [user, setUser] = useState<Profile | null>(null);
  const [className, setClassName] = useState("未分配班级");
  const [currentPassword, setCurrentPassword] = useState(""); const [newPassword, setNewPassword] = useState(""); const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null); const [message, setMessage] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  useEffect(() => {
    void Promise.all([api<Profile>("/api/v1/auth/me"), loadOptions<ClassItem>("/api/v1/classes")]).then(([profile, classes]) => {
      setUser(profile); setClassName(classes.find((c) => c.id === profile.class_id)?.class_name ?? (profile.class_id ? `班级 ${profile.class_id}` : "未分配班级"));
    }).catch((e) => setError(e.message));
  }, []);
  async function changePassword(event: FormEvent) {
    event.preventDefault(); setError(null); setMessage(null);
    if (newPassword !== confirmPassword) { setError("两次输入的新密码不一致"); return; }
    setBusy(true);
    try {
      await api("/api/v1/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) });
      setMessage("密码已更新，请使用新密码重新登录。");
      setToken(null); window.localStorage.removeItem("wolin_user");
      setTimeout(() => window.location.replace("/"), 900);
    } catch (e) { setError(e instanceof Error ? e.message : "修改密码失败"); }
    finally { setBusy(false); }
  }
  if (!user) return <div><ErrorText error={error} />{!error && <p className="text-sm text-slate-400">正在读取账号信息…</p>}</div>;
  return <div className="max-w-3xl">
    <Link href="/dashboard" className="mb-5 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-indigo-600"><ArrowLeft size={13} />返回工作台</Link>
    <PageHeader title="个人信息" eyebrow="ACCOUNT PROFILE" desc="查看当前登录账号资料并修改自己的登录密码。" />
    <ErrorText error={error} /><SuccessText message={message} />
    <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-6">
      <div className="flex items-center gap-4"><span className="grid h-14 w-14 place-items-center rounded-2xl bg-indigo-50 text-indigo-600"><UserRound size={26} /></span><div><h2 className="text-lg font-semibold text-slate-800">{user.display_name}</h2><p className="mt-1 text-xs text-slate-400">账号 {user.username}</p></div><Badge tone={user.is_active ? "green" : "rose"}>{user.is_active ? "账号启用" : "账号停用"}</Badge></div>
      <div className="mt-6 grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-3"><Info label="账号 ID" value={user.id} /><Info label="当前角色" value={ROLE_LABELS[user.role] ?? user.role} /><Info label="所属班级" value={className} /></div>
      <div className="mt-4 flex items-center gap-2 text-[11px] text-slate-400"><ShieldCheck size={13} />用户资料不包含密码哈希；业务操作由后端按角色校验。</div>
      {(user.role === "admin" || user.role === "head_teacher") ? <Link href="/users" className="mt-5 inline-flex rounded-lg bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-600">打开用户管理</Link> : null}
    </section>
    <section className="rounded-2xl border border-slate-200 bg-white p-6"><h2 className="flex items-center gap-2 text-sm font-semibold text-slate-800"><KeyRound size={16} className="text-indigo-500" />修改登录密码</h2><p className="mb-5 mt-2 text-xs text-slate-400">请输入当前密码和新密码。修改后旧令牌会失效，需要重新登录。</p>
      <form onSubmit={changePassword} className="grid max-w-xl gap-4"><Field label="当前密码"><input required type="password" autoComplete="current-password" className={inputClass} value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} /></Field><Field label="新密码（至少 6 位）"><input required minLength={6} maxLength={72} type="password" autoComplete="new-password" className={inputClass} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /></Field><Field label="确认新密码"><input required minLength={6} maxLength={72} type="password" autoComplete="new-password" className={inputClass} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} /></Field><div><Button type="submit" disabled={busy}>{busy ? "正在更新…" : "更新密码"}</Button></div></form>
    </section>
  </div>;
}
function Info({ label, value }: { label: string; value: string | number }) { return <div><p className="text-[10px] text-slate-400">{label}</p><p className="mt-1.5 text-sm font-medium text-slate-700">{value}</p></div>; }
