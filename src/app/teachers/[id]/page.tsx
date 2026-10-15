"use client";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, BookOpen, CalendarDays, Mail, PencilLine, Phone, School, UserRound } from "lucide-react";
import { api } from "@/lib/client";
import type { Relation, Teacher } from "@/lib/contracts";
import { Badge, Button, EmptyState, ErrorText, PageHeader, StatCard, Table } from "@/components/ui";
import { TeacherForm } from "@/components/TeacherForm";

type Detail = Teacher & { relations: Relation[] };
export default function TeacherDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params); const [data, setData] = useState<Detail | null>(null); const [error, setError] = useState<string | null>(null); const [editing, setEditing] = useState(false);
  async function load() { try { setData(await api<Detail>(`/api/v1/teachers/${id}`)); setError(null); } catch (e) { setError(e instanceof Error ? e.message : "加载失败"); } }
  useEffect(() => { void load(); }, [id]);
  if (!data) return <div><ErrorText error={error} />{!error && <p className="text-sm text-slate-400">正在读取教师详情…</p>}</div>;
  const rows = data.relations;
  return <div><Link href="/teachers" className="mb-5 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-indigo-600"><ArrowLeft size={13} />返回教师管理</Link><PageHeader title={`${data.name} · 教师档案`} eyebrow={`TEACHER PROFILE · ${data.teacher_no}`} desc={`${data.specialty ?? "教学专长未填写"}　·　教学年限 ${data.teaching_years} 年`} action={<Button tone="ghost" onClick={() => setEditing(true)}><PencilLine size={14} />编辑档案</Button>} /><ErrorText error={error} />
    <div className="mb-6 grid gap-4 sm:grid-cols-3"><StatCard label="关联班级" value={new Set(rows.map((r) => r.class_id)).size} icon={<School size={20} />} description="按有效关系去重" /><StatCard label="担任班主任" value={rows.filter((r) => r.relation_type === "班主任" && r.class_status !== "已结课").length} icon={<UserRound size={20} />} description="仅未结课班级" /><StatCard label="授课班级" value={rows.filter((r) => r.relation_type === "授课老师").length} icon={<BookOpen size={20} />} description="包含已结课班级历史安排" /></div>
    <div className="mb-6 grid gap-4 rounded-xl border border-slate-200 bg-white p-5 sm:grid-cols-4"><div><p className="text-[10px] text-slate-400">教师 ID</p><p className="mt-2 text-sm text-slate-700">{data.id}</p></div><div><p className="flex items-center gap-1 text-[10px] text-slate-400"><Phone size={11} />联系电话</p><p className="mt-2 text-sm text-slate-700">{data.phone ?? "未填写"}</p></div><div><p className="flex items-center gap-1 text-[10px] text-slate-400"><Mail size={11} />补充联系方式</p><p className="mt-2 text-sm text-slate-700">{data.contact_info ?? "未填写"}</p></div><div><p className="text-[10px] text-slate-400">任职 / 授课状态</p><div className="mt-2 flex gap-1"><Badge tone={data.teacher_status === "在职" ? "green" : "slate"}>{data.teacher_status}</Badge><Badge tone={data.teaching_status === "可授课" ? "indigo" : "amber"}>{data.teaching_status}</Badge></div></div></div>
    <section><div className="mb-4 flex items-center justify-between"><h2 className="text-sm font-semibold">关联班级与担任角色</h2><Link href={`/scheduling?teacher_id=${id}`}><Button><CalendarDays size={14} />管理排班关系</Button></Link></div><Table headers={["班级", "状态", "担任角色", "建立时间", "跳转"]}>{rows.map((r) => <tr key={r.id}><td className="px-5 py-4"><Link href={`/classes/${r.class_id}`} className="font-medium text-indigo-600">{r.class_name}</Link><p className="mt-1 text-[10px] text-slate-400">{r.class_no}</p></td><td className="px-5 py-4"><Badge tone={r.class_status === "在读" ? "green" : "slate"}>{r.class_status}</Badge></td><td className="px-5 py-4"><Badge tone={r.relation_type === "班主任" ? "indigo" : "slate"}>{r.relation_type}</Badge></td><td className="px-5 py-4 text-xs text-slate-500">{new Date(r.created_at).toLocaleDateString("zh-CN")}</td><td className="px-5 py-4"><Link href={`/classes/${r.class_id}`} className="inline-flex items-center gap-1 text-xs text-indigo-600">查看班级学情<ArrowUpRight size={12} /></Link></td></tr>)}{!rows.length && <EmptyState columns={5} title="暂无有效班级关系" />}</Table></section>
    {editing && <TeacherForm teacher={data} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); void load(); }} />}
  </div>;
}
