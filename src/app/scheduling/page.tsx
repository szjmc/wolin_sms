"use client";
import Link from "next/link";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { CalendarDays, Info, Link2, RefreshCw, Unlink } from "lucide-react";
import { api, type PageResult } from "@/lib/client";
import type { ClassItem, Relation, Teacher } from "@/lib/contracts";
import { loadOptions, queryString } from "@/lib/options";
import { Badge, Button, EmptyState, ErrorText, Field, inputClass, PageHeader, Pagination, SuccessText } from "@/components/ui";

export default function SchedulingPage() { return <Suspense fallback={<p>正在加载教师排班…</p>}><Scheduling /></Suspense>; }
function Scheduling() {
  const params = useSearchParams(); const [classes, setClasses] = useState<ClassItem[]>([]); const [teachers, setTeachers] = useState<Teacher[]>([]); const [allRelations, setAllRelations] = useState<Relation[]>([]);
  const [classId, setClassId] = useState(""); const [teacherId, setTeacherId] = useState(""); const [role, setRole] = useState("授课老师");
  const [filters, setFilters] = useState({ class_id: "", teacher_id: "", relation_type: "" }); const [data, setData] = useState<PageResult<Relation> | null>(null);
  const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null); const [message, setMessage] = useState<string | null>(null);
  async function metadata() { const [c, t, r] = await Promise.all([loadOptions<ClassItem>("/api/v1/classes"), loadOptions<Teacher>("/api/v1/teachers"), loadOptions<Relation>("/api/v1/class-teacher-relations")]); setClasses(c); setTeachers(t); setAllRelations(r); }
  async function load(values = filters, page = 1) { setLoading(true); try { setData(await api<PageResult<Relation>>(`/api/v1/class-teacher-relations?${queryString({ ...values, page, page_size: 10 })}`)); } catch (e) { setError(e instanceof Error ? e.message : "加载失败"); } finally { setLoading(false); } }
  useEffect(() => { setClassId(params.get("class_id") ?? ""); setTeacherId(params.get("teacher_id") ?? ""); setFilters({ class_id: params.get("class_id") ?? "", teacher_id: params.get("teacher_id") ?? "", relation_type: "" }); void metadata().catch((e) => setError(e.message)); }, [params]);
  useEffect(() => { void load(filters); }, [filters]);
  function unavailable(t: Teacher) {
    if (t.teacher_status !== "在职" || t.teaching_status !== "可授课") return `${t.teacher_status} / ${t.teaching_status}`;
    // 铁律 1：老师在任何未结课班级有有效关系就算被占用（不分角色）。
    const busy = allRelations.find((r) => r.teacher_id === t.id && r.class_status !== "已结课");
    if (busy && String(busy.class_id) !== classId) return `已负责 ${busy.class_no}（${busy.relation_type}）`;
    // 铁律 2：同班另一种角色也不能兼，班主任和授课老师必须是两个人。
    if (busy && String(busy.class_id) === classId && busy.relation_type !== role) return "班主任和授课老师不能是同一人";
    // 铁律 3：目标班级已有别的班主任时，不能再加班主任。
    if (role === "班主任") {
      const current = allRelations.find((r) => String(r.class_id) === classId && r.relation_type === "班主任");
      if (current && current.teacher_id !== t.id) return "所选班级已有班主任";
    }
    return null;
  }
  async function bind(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null); setMessage(null);
    try { const row = await api<{ id: number }>(`/api/v1/classes/${classId}/teachers/${teacherId}`, { method: "PUT", body: JSON.stringify({ relation_type: role }) });
      setMessage(`已绑定${role}关系（关系 ID ${row.id}）。相同有效关系重复提交不会新增。`); await metadata(); await load(filters); }
    catch (e) { setError(e instanceof Error ? e.message : "绑定失败"); } finally { setBusy(false); }
  }
  async function unlink(r: Relation) {
    if (!confirm(`解除 ${r.teacher_name} 在 ${r.class_no} 的「${r.relation_type}」关系？历史记录会保留。`)) return;
    setBusy(true); setError(null); setMessage(null);
    try { await api(`/api/v1/classes/${r.class_id}/teachers/${r.teacher_id}?relation_type=${encodeURIComponent(r.relation_type)}`, { method: "DELETE" }); setMessage("排班关系已解除，历史数据完整保留。"); await metadata(); await load(filters); }
    catch (e) { setError(e instanceof Error ? e.message : "解除失败"); } finally { setBusy(false); }
  }
  return <div>
    <PageHeader title="班级排班与教师关系" eyebrow="CLASS & TEACHER SCHEDULING" desc="关联班级与教师，统一维护班主任和授课老师角色。" />
    <section className="mb-6 rounded-xl border border-indigo-200 bg-indigo-50/40 p-6"><div className="flex items-center gap-2"><Link2 size={17} className="text-indigo-600" /><h2 className="text-sm font-semibold text-slate-800">分配授课或班主任角色</h2></div><p className="mb-5 mt-2 text-xs leading-6 text-indigo-400">关系绑定具有幂等性；解除关系同样采用逻辑删除，历史数据安全保留。</p>
      <form className="grid items-end gap-4 sm:grid-cols-2 xl:grid-cols-4" onSubmit={bind}><Field label="选择班级"><select className={inputClass} required value={classId} onChange={(e) => { setClassId(e.target.value); setTeacherId(""); }}><option value="">请选择班级</option>{classes.map((c) => <option key={c.id} value={c.id} disabled={c.class_status === "已结课"}>{c.class_no}（{c.class_name}）{c.class_status === "已结课" ? " · 已结课" : ""}</option>)}</select></Field><Field label="选择教师"><select className={inputClass} required value={teacherId} onChange={(e) => setTeacherId(e.target.value)}><option value="">请选择教师</option>{teachers.map((t) => <option key={t.id} value={t.id} disabled={!!unavailable(t)}>{t.name}（{t.teacher_no} · ID {t.id}）{unavailable(t) ? ` · ${unavailable(t)}` : ""}</option>)}</select></Field><Field label="担任角色"><select className={inputClass} value={role} onChange={(e) => { setRole(e.target.value); setTeacherId(""); }}><option>授课老师</option><option>班主任</option></select></Field><Button type="submit" disabled={busy || !classId || !teacherId || classes.find((c) => String(c.id) === classId)?.class_status === "已结课"} className="!h-11"><Link2 size={14} />绑定角色关联</Button></form>
      <p className="mt-4 flex items-start gap-1.5 text-[10px] leading-5 text-slate-400"><Info size={13} className="mt-0.5 shrink-0" />仅在职且可授课老师可分配。一人只负责一个未结课班级；班主任与授课老师不能是同一人；每班最多一位班主任。已结课关系保留为历史，不占用老师。</p>
    </section>
    <ErrorText error={error} /><SuccessText message={message} />
    <section className="rounded-xl border border-slate-200 bg-white"><div className="flex flex-wrap items-center justify-between gap-3 px-5 py-5"><div className="flex items-center gap-2"><CalendarDays size={17} className="text-indigo-500" /><h2 className="text-sm font-semibold text-slate-800">当前生效的班级教师排课清单</h2><Badge tone="indigo">{data?.total ?? 0} 条</Badge></div><Button tone="ghost" className="!py-2" onClick={() => { void metadata(); void load(filters, data?.page ?? 1); }}><RefreshCw size={14} className={loading ? "animate-spin" : ""} />刷新</Button></div>
      <div className="grid gap-3 border-t border-slate-100 bg-slate-50/40 px-5 py-4 sm:grid-cols-3"><Field label="班级筛选"><select className={inputClass} value={filters.class_id} onChange={(e) => setFilters({ ...filters, class_id: e.target.value })}><option value="">全部班级</option>{classes.map((c) => <option key={c.id} value={c.id}>{c.class_no}</option>)}</select></Field><Field label="教师筛选"><select className={inputClass} value={filters.teacher_id} onChange={(e) => setFilters({ ...filters, teacher_id: e.target.value })}><option value="">全部老师</option>{teachers.map((t) => <option key={t.id} value={t.id}>{t.name}（{t.teacher_no}）</option>)}</select></Field><Field label="角色筛选"><select className={inputClass} value={filters.relation_type} onChange={(e) => setFilters({ ...filters, relation_type: e.target.value })}><option value="">全部角色</option><option>班主任</option><option>授课老师</option></select></Field></div>
      <div className="overflow-x-auto"><table className="w-full whitespace-nowrap text-left text-[13px]"><thead className="border-y border-slate-100 bg-slate-50 text-[11px] text-slate-500"><tr>{["班级编号", "班级名称", "教师姓名 / 编号", "担任角色", "教师专长", "联系电话", "操作"].map((h) => <th key={h} className="px-5 py-3.5 font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{data?.items.map((r) => <tr key={r.id} className="hover:bg-indigo-50/30"><td className="px-5 py-4"><Link href={`/classes/${r.class_id}`} className="font-medium text-slate-700 hover:text-indigo-600">{r.class_no}</Link></td><td className="px-5 py-4"><Link href={`/classes/${r.class_id}`} className="text-slate-600 hover:text-indigo-600">{r.class_name}</Link><p className="mt-1 text-[10px] text-slate-400">{r.class_status}</p></td><td className="px-5 py-4"><Link href={`/teachers/${r.teacher_id}`} className="font-medium text-indigo-600">{r.teacher_name}</Link><p className="mt-1 text-[10px] text-slate-400">{r.teacher_no} · ID {r.teacher_id}</p></td><td className="px-5 py-4"><Badge tone={r.relation_type === "班主任" ? "indigo" : "green"}>{r.relation_type}</Badge></td><td className="px-5 py-4 text-xs text-slate-500">{r.specialty ?? "—"}</td><td className="px-5 py-4 text-xs text-slate-500">{r.phone ?? "未填写"}</td><td className="px-5 py-4"><button disabled={busy} onClick={() => unlink(r)} className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2.5 py-1.5 text-xs text-rose-500"><Unlink size={12} />解除排课</button></td></tr>)}{(!data || !data.items.length) && <EmptyState title={loading ? "正在读取排班…" : "暂无有效排班关系"} columns={7} />}</tbody></table></div><div className="px-5 pb-5">{data && <Pagination page={data.page} total={data.total} pageSize={data.page_size} onPage={(p) => load(filters, p)} />}</div>
    </section>
  </div>;
}
