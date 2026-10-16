"use client";
import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowLeft, KeyRound, Plus, RefreshCw, Search, Shield, UserCog, UserRound, UserX } from "lucide-react";
import { api, type PageResult } from "@/lib/client";
import type { ClassItem } from "@/lib/contracts";
import { ROLE_LABELS } from "@/lib/auth-client";
import { loadOptions, queryString } from "@/lib/options";
import { Badge, Button, EmptyState, ErrorText, Field, inputClass, Modal, PageHeader, Pagination } from "@/components/ui";

interface UserRow {
  id: number; username: string; display_name: string; role: string; class_id: number | null;
  is_active: boolean; created_at: string; updated_at: string;
}
const ROLES = ["admin", "head_teacher", "teacher", "employment", "viewer"];
const EMPTY = { username: "", display_name: "", password: "", role: "viewer", class_id: "", is_active: true };

export default function UsersPage() {
  const [me, setMe] = useState<UserRow | null>(null); const [rows, setRows] = useState<PageResult<UserRow> | null>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]); const [search, setSearch] = useState(""); const [roleFilter, setRoleFilter] = useState("");
  const [page, setPage] = useState(1); const [form, setForm] = useState<UserRow | "new" | null>(null);
  const [values, setValues] = useState(EMPTY); const [error, setError] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const isAdmin = me?.role === "admin";

  async function load(p = page) {
    setBusy(true); setError(null);
    try {
      const [u, list] = await Promise.all([
        api<UserRow>("/api/v1/auth/me"),
        api<PageResult<UserRow>>(`/api/v1/users?${queryString({ username: search, role: roleFilter, page: p, page_size: 12 })}`),
      ]);
      if (u.role !== "admin" && u.role !== "head_teacher") { window.location.replace("/dashboard"); return; }
      setMe(u); setRows(list);
    } catch (e) { setError(e instanceof Error ? e.message : "无法加载用户列表"); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    void load(1);
    void loadOptions<ClassItem>("/api/v1/classes").then(setClasses).catch(() => undefined);
  }, []);

  function openCreate() { setForm("new"); setValues({ ...EMPTY, role: isAdmin ? "viewer" : "teacher" }); }
  function openEdit(row: UserRow) { setForm(row); setValues({ username: row.username, display_name: row.display_name, password: "", role: row.role, class_id: row.class_id ? String(row.class_id) : "", is_active: row.is_active }); }
  async function save(event: FormEvent) {
    event.preventDefault(); setError(null); setBusy(true);
    const isNew = form === "new";
    const payload: Record<string, unknown> = isNew
      ? { username: values.username, display_name: values.display_name, password: values.password, role: values.role, class_id: values.class_id ? Number(values.class_id) : null }
      : { display_name: values.display_name, role: values.role, class_id: values.class_id ? Number(values.class_id) : null, is_active: values.is_active, ...(values.password ? { password: values.password } : {}) };
    try {
      const result = await api<UserRow>(isNew ? "/api/v1/users" : `/api/v1/users/${(form as UserRow).id}`, { method: isNew ? "POST" : "PATCH", body: JSON.stringify(payload) });
      setForm(null); await load(page);
      if (!isNew && result.is_active !== (form as UserRow).is_active) setError("账号状态已更新");
    } catch (e) { setError(e instanceof Error ? e.message : "保存用户失败"); }
    finally { setBusy(false); }
  }
  async function toggle(user: UserRow) {
    if (user.id === me?.id) { setError("不能停用当前登录账号"); return; }
    if (!confirm(`${user.is_active ? "停用" : "启用"}账号 ${user.username}？`)) return;
    try { await api(`/api/v1/users/${user.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !user.is_active }) }); await load(page); }
    catch (e) { setError(e instanceof Error ? e.message : "更新账号状态失败"); }
  }
  async function remove(user: UserRow) {
    if (user.id === me?.id) { setError("不能删除当前登录账号"); return; }
    if (!confirm(`确认逻辑删除账号 ${user.username}？该账号将无法再登录。`)) return;
    try { await api(`/api/v1/users/${user.id}`, { method: "DELETE" }); await load(page); }
    catch (e) { setError(e instanceof Error ? e.message : "删除用户失败"); }
  }
  const managerCannotTouchAdmin = !isAdmin;

  return <div>
    <Link href="/dashboard" className="mb-5 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-indigo-600"><ArrowLeft size={13} />返回工作台</Link>
    <PageHeader title="用户管理" eyebrow="ACCOUNT MANAGEMENT" desc="管理员与班主任可以查看全部账号并维护普通用户；仅管理员可以授予管理员角色。" action={<Button onClick={openCreate}><Plus size={15} />新增用户</Button>} />
    <ErrorText error={error} />
    <section className="mb-5 rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-center gap-2 text-xs font-semibold text-slate-700"><UserCog size={15} className="text-indigo-500" />用户账号列表<Badge tone="indigo">{rows?.total ?? 0} 个账号</Badge></div>
      <form className="grid gap-3 sm:grid-cols-[1fr_220px_auto_auto]" onSubmit={(e) => { e.preventDefault(); setPage(1); void load(1); }}>
        <Field label="用户名 / 登录账号"><div className="relative"><Search size={14} className="absolute left-3 top-3.5 text-slate-400" /><input className={`${inputClass} !pl-9`} value={search} onChange={(e) => setSearch(e.target.value)} placeholder="输入账号关键词" /></div></Field>
        <Field label="角色筛选"><select className={inputClass} value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}><option value="">全部角色</option>{ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}</select></Field>
        <Button type="submit" className="self-end"><Search size={14} />查询</Button><Button tone="ghost" className="self-end" onClick={() => { setSearch(""); setRoleFilter(""); setPage(1); void load(1); }}><RefreshCw size={14} />刷新</Button>
      </form>
    </section>
    <section className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between px-5 py-4"><h2 className="text-sm font-semibold text-slate-800">全部用户信息</h2><span className="text-[11px] text-slate-400">不显示密码或密码哈希</span></div>
      <div className="overflow-x-auto"><table className="w-full whitespace-nowrap text-left text-[13px]"><thead className="border-y border-slate-100 bg-slate-50 text-[11px] text-slate-500"><tr>{["账号 / 显示名", "角色", "所属班级", "状态", "创建时间", "操作"].map((h) => <th key={h} className="px-5 py-3.5 font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">
        {rows?.items.map((u) => <tr key={u.id} className="hover:bg-slate-50/70"><td className="px-5 py-4"><p className="font-medium text-slate-800">{u.username}{u.id === me?.id && <span className="ml-2 text-[10px] text-indigo-500">（当前账号）</span>}</p><p className="mt-1 text-[10px] text-slate-400">{u.display_name} · ID {u.id}</p></td><td className="px-5 py-4"><Badge tone={u.role === "admin" ? "indigo" : "slate"}>{ROLE_LABELS[u.role] ?? u.role}</Badge></td><td className="px-5 py-4 text-xs text-slate-500">{classes.find((c) => c.id === u.class_id)?.class_no ?? (u.class_id ? `班级 ${u.class_id}` : "不限定班级")}</td><td className="px-5 py-4"><Badge tone={u.is_active ? "green" : "rose"}>{u.is_active ? "启用" : "停用"}</Badge></td><td className="px-5 py-4 text-[11px] text-slate-400">{new Date(u.created_at).toLocaleDateString("zh-CN")}</td><td className="px-5 py-4"><div className="flex gap-3 text-xs">{!(managerCannotTouchAdmin && u.role === "admin") ? <><button className="text-indigo-600" onClick={() => openEdit(u)}>编辑 / 重置密码</button>{u.id !== me?.id && <button className="text-slate-500" onClick={() => toggle(u)}>{u.is_active ? "停用" : "启用"}</button>}{u.id !== me?.id && <button className="text-rose-500" onClick={() => remove(u)}>删除</button>}</> : <span className="text-slate-300">管理员账号（只读）</span>}</div></td></tr>)}
        {(!rows || !rows.items.length) && <EmptyState title={busy ? "正在加载账号…" : "暂无用户"} columns={6} />}
      </tbody></table></div>
      <div className="px-5 pb-5">{rows && <Pagination page={rows.page} total={rows.total} pageSize={rows.page_size} onPage={(p) => { setPage(p); void load(p); }} />}</div>
    </section>
    {form && <Modal title={form === "new" ? "新增用户账号" : `编辑用户 · ${(form as UserRow).username}`} error={error} saving={busy} onClose={() => setForm(null)} onSubmit={save}>
      <p className="text-[11px] text-slate-400">密码会加密保存，列表与响应中不会显示密码。</p>
      {form === "new" ? <Field label="登录账号 *"><input required minLength={3} maxLength={50} className={inputClass} value={values.username} onChange={(e) => setValues({ ...values, username: e.target.value })} /></Field> : null}
      <Field label="显示名称 *"><input required maxLength={50} className={inputClass} value={values.display_name} onChange={(e) => setValues({ ...values, display_name: e.target.value })} /></Field>
      <Field label={form === "new" ? "初始密码 *" : "重置密码（留空不修改）"}><input type="password" required={form === "new"} minLength={6} maxLength={72} autoComplete="new-password" className={inputClass} value={values.password} onChange={(e) => setValues({ ...values, password: e.target.value })} /></Field>
      <Field label="角色"><select className={inputClass} value={values.role} onChange={(e) => setValues({ ...values, role: e.target.value, class_id: ["head_teacher", "teacher"].includes(e.target.value) ? values.class_id : "" })}>{ROLES.filter((r) => isAdmin || r !== "admin").map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}</select></Field>
      {["head_teacher", "teacher"].includes(values.role) ? <Field label="所属班级 *"><select required className={inputClass} value={values.class_id} onChange={(e) => setValues({ ...values, class_id: e.target.value })}><option value="">请选择班级</option>{classes.map((c) => <option key={c.id} value={c.id}>{c.class_no} · {c.class_name}</option>)}</select></Field> : null}
      {form !== "new" ? <label className="flex items-center gap-2 text-xs text-slate-600"><input type="checkbox" checked={values.is_active} onChange={(e) => setValues({ ...values, is_active: e.target.checked })} />账号启用</label> : null}
      <p className="text-[11px] leading-5 text-slate-400">{isAdmin ? "管理员可以管理所有账号与角色。" : "班主任可管理普通用户；管理员账号不可编辑，且不能授予管理员角色。"}</p>
    </Modal>}
  </div>;
}
