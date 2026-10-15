"use client";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, BriefcaseBusiness, CalendarDays, MapPin, PencilLine } from "lucide-react";
import { api } from "@/lib/client";
import type { Employment, Student } from "@/lib/contracts";
import { loadOptions } from "@/lib/options";
import { Badge, Button, ErrorText, PageHeader } from "@/components/ui";
import { SalaryComparisonPanel } from "@/components/SalaryComparison";
import { EmploymentForm } from "@/components/EmploymentForm";
export default function EmploymentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params); const [record, setRecord] = useState<Employment | null>(null); const [students, setStudents] = useState<Student[]>([]); const [error, setError] = useState<string | null>(null); const [editing, setEditing] = useState(false);
  async function load() { try { const [r, s] = await Promise.all([api<Employment>(`/api/v1/employment-records/${id}`), loadOptions<Student>("/api/v1/students")]); setRecord(r); setStudents(s); setError(null); } catch (e) { setError(e instanceof Error ? e.message : "加载失败"); } }
  useEffect(() => { void load(); }, [id]);
  if (!record) return <div><ErrorText error={error} />{!error && <p className="text-sm text-slate-400">正在读取就业记录…</p>}</div>;
  const duration = record.offer_date && record.employment_open_date ? Math.round((new Date(record.offer_date).getTime() - new Date(record.employment_open_date).getTime()) / 86400000) : null;
  return <div><Link href="/employment" className="mb-5 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-indigo-600"><ArrowLeft size={13} />返回就业管理</Link><PageHeader title={`${record.student_name_snapshot} · 就业详情`} eyebrow={`EMPLOYMENT RECORD · #${record.id}`} desc="独立保存本次就业过程，原始薪资与以往信息清晰可追溯。" action={<Button tone="ghost" onClick={() => setEditing(true)}><PencilLine size={14} />编辑本条记录</Button>} /><ErrorText error={error} />
    <div className="grid gap-6 xl:grid-cols-[1fr_1.2fr]"><section className="h-fit rounded-xl border border-slate-200 bg-white p-6"><div className="mb-5 flex items-center gap-3"><span className="grid h-12 w-12 place-items-center rounded-xl bg-indigo-50 text-indigo-500"><BriefcaseBusiness size={22} /></span><div><h2 className="text-base font-semibold text-slate-800">{record.company_name}</h2><p className="mt-1 flex items-center gap-1 text-xs text-slate-400"><MapPin size={11} />{record.employment_city ?? "城市未填写"} · {record.position ?? "岗位未填写"}</p></div></div>
      <dl className="grid gap-5 border-t border-slate-100 pt-5 sm:grid-cols-2">{[["学生姓名快照", record.student_name_snapshot], ["班级编号快照", record.class_no_snapshot], ["就业开放日期", record.employment_open_date], ["Offer 日期", record.offer_date], ["就业时长", duration === null ? "日期不完整，暂不能计算" : `${duration} 自然日`], ["原学历毕业日期", record.past_graduation_date], ["毕业年限", record.graduation_years === null ? "—" : `${record.graduation_years} 年`], ["记录创建时间", record.created_at ? new Date(record.created_at).toLocaleString("zh-CN") : "—"]].map(([label, value]) => <div key={label}><dt className="text-[10px] text-slate-400">{label}</dt><dd className="mt-2 text-xs text-slate-600">{value ?? "未填写"}</dd></div>)}</dl>
      <div className="mt-6 space-y-3 border-t border-slate-100 pt-5"><Link href={`/students/${record.student_id}`} className="flex items-center justify-between text-xs text-indigo-600">查看学生完整档案<ArrowUpRight size={13} /></Link>{record.class_id && <Link href={`/classes/${record.class_id}`} className="flex items-center justify-between text-xs text-indigo-600">查看历史班级详情<ArrowUpRight size={13} /></Link>}<Link href={`/scores?student_id=${record.student_id}&q=${encodeURIComponent(record.student_no ?? record.student_name_snapshot)}`} className="flex items-center justify-between text-xs text-indigo-600">查看该学生考核成绩<ArrowUpRight size={13} /></Link></div>
    </section><section className="rounded-xl border border-slate-200 bg-white p-6"><h2 className="mb-5 text-sm font-semibold text-slate-800">岗位与薪资成长对比</h2><SalaryComparisonPanel key={record.updated_at} recordId={record.id} /></section></div>
    {editing && <EmploymentForm record={record} students={students} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); void load(); }} />}
  </div>;
}
