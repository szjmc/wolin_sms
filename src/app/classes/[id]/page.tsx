"use client";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, BookOpenCheck, BriefcaseBusiness, CalendarDays, CheckCircle2, GraduationCap, Users } from "lucide-react";
import { api, type PageResult } from "@/lib/client";
import type { ClassItem, ClassOverview, Employment, Student } from "@/lib/contracts";
import { displayMoney, loadOptions } from "@/lib/options";
import { Badge, Button, Dialog, EmptyState, ErrorText, Field, inputClass, PageHeader, Pagination, StatCard } from "@/components/ui";

export default function ClassDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params); const [data, setData] = useState<ClassOverview | null>(null); const [students, setStudents] = useState<PageResult<Student> | null>(null); const [employment, setEmployment] = useState<PageResult<Employment> | null>(null);
  const [tab, setTab] = useState("students"); const [error, setError] = useState<string | null>(null);
  const [allClasses, setAllClasses] = useState<ClassItem[]>([]); const [moving, setMoving] = useState<Student | null>(null); const [targetClass, setTargetClass] = useState(""); const [busy, setBusy] = useState(false);
  async function loadStudents(page = 1) { try { setStudents(await api<PageResult<Student>>(`/api/v1/students?class_id=${id}&page=${page}&page_size=10`)); } catch (e) { setError(e instanceof Error ? e.message : "加载失败"); } }
  async function loadEmployment(page = 1) { try { setEmployment(await api<PageResult<Employment>>(`/api/v1/classes/${id}/employment-records?page=${page}&page_size=10`)); } catch (e) { setError(e instanceof Error ? e.message : "加载失败"); } }
  useEffect(() => { void api<ClassOverview>(`/api/v1/classes/${id}/overview`).then(setData).catch((e) => setError(e.message)); void loadStudents(); void loadEmployment(); void loadOptions<ClassItem>("/api/v1/classes").then(setAllClasses).catch(() => undefined); }, [id]);
  // 调整学生班级：把选中学生转到目标班，成功后刷新班级学情
  async function moveStudent() {
    if (!moving || !targetClass) return;
    setBusy(true); setError(null);
    try {
      await api(`/api/v1/students/${moving.id}`, { method: "PATCH", body: JSON.stringify({ class_id: Number(targetClass) }) });
      setMoving(null); setTargetClass("");
      await Promise.all([loadStudents(), api<ClassOverview>(`/api/v1/classes/${id}/overview`).then(setData)]);
    } catch (e) { setError(e instanceof Error ? e.message : "调整班级失败"); } finally { setBusy(false); }
  }
  if (!data) return <div><Link href="/classes" className="text-xs text-indigo-600">← 返回班级管理</Link><div className="mt-5"><ErrorText error={error} />{!error && <p className="text-sm text-slate-400">正在加载班级详情…</p>}</div></div>;
  const c = data.class_info;
  return <div><Link href="/classes" className="mb-5 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-indigo-600"><ArrowLeft size={13} />返回班级管理</Link>
    <PageHeader title={c.class_name} eyebrow={`CLASS OVERVIEW · ${c.class_no}`} desc={`开班 ${c.start_date}　${c.completion_date ? `结课 ${c.completion_date}` : "尚未记录结课时间"}`} action={<div className="flex items-center gap-3"><Badge tone={c.class_status === "在读" ? "green" : "slate"}>{c.class_status}</Badge><Link href={`/scheduling?class_id=${id}`}><Button><CalendarDays size={15} />管理教师排班</Button></Link></div>} />
    <ErrorText error={error} />
    <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label="班级学生" value={data.total_students} icon={<Users size={20} />} description={`男 ${data.male_count} · 女 ${data.female_count} · 其他 ${data.other_count}`} /><StatCard label="成绩及格率" value={data.pass_rate === null ? "暂无成绩" : `${data.pass_rate}%`} icon={<CheckCircle2 size={20} />} description={`有效成绩中 ${data.passing_scores} / ${data.total_scores} 条 ≥ 60`} /><StatCard label="班级平均分" value={data.average_score ?? "—"} icon={<BookOpenCheck size={20} />} description={`${data.graded_students} 人已有成绩 · ${data.qualified_students} 人全部达标`} /><StatCard label="已就业学生" value={data.employed_students} icon={<BriefcaseBusiness size={20} />} description="按就业记录班级快照去重" /></div>
    <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5"><h2 className="mb-4 text-sm font-semibold text-slate-800">班级教学团队</h2><div className="grid gap-4 md:grid-cols-2"><div className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-4"><p className="mb-2 text-[10px] font-medium text-indigo-500">班主任</p>{c.head_teacher ? <Link href={`/teachers/${c.head_teacher.id}`} className="flex items-center justify-between"><div><p className="text-sm font-semibold text-slate-800">{c.head_teacher.name}<span className="ml-2 text-[10px] font-normal text-slate-400">{c.head_teacher.teacher_no} · ID {c.head_teacher.id}</span></p><p className="mt-1.5 text-[11px] text-slate-400">{c.head_teacher.specialty ?? "暂无专长信息"} · {c.head_teacher.phone ?? "电话未填写"}</p></div><ArrowUpRight size={15} className="text-indigo-500" /></Link> : <p className="text-xs text-slate-400">暂未安排班主任</p>}</div><div className="rounded-lg border border-slate-200 p-4"><p className="mb-2 text-[10px] text-slate-400">任课老师 · {c.teachers.length} 人</p><div className="space-y-2">{c.teachers.map((t) => <Link key={t.id} href={`/teachers/${t.id}`} className="flex items-center justify-between text-xs"><span className="font-medium text-slate-700">{t.name}<span className="ml-2 text-[10px] font-normal text-slate-400">{t.teacher_no} · {t.specialty ?? ""}</span></span><ArrowUpRight size={13} className="text-slate-400" /></Link>)}{!c.teachers.length && <p className="text-xs text-slate-400">暂无任课老师</p>}</div></div></div></section>
    <section className="rounded-xl border border-slate-200 bg-white"><div className="flex flex-wrap items-center justify-between border-b border-slate-100 px-5"><div className="flex gap-6">{[["students", "班级学生"], ["employment", "就业历史"]].map(([key, label]) => <button key={key} onClick={() => setTab(key)} className={`border-b-2 py-4 text-xs font-medium ${tab === key ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-400"}`}>{label}</button>)}</div><Link href={tab === "students" ? `/scores?class_id=${id}` : `/employment?class_id=${id}`} className="inline-flex items-center gap-1 text-xs text-indigo-600">{tab === "students" ? "查看班级全员成绩" : "筛选班级就业记录"}<ArrowUpRight size={13} /></Link></div>
      <div className="overflow-x-auto">{tab === "students" ? <table className="w-full whitespace-nowrap text-left text-[13px]"><thead className="bg-slate-50 text-[11px] text-slate-500"><tr>{["学生 / 学号", "性别 / 年龄", "学历 / 原毕业院校", "培训入学日期", "关联操作"].map((h) => <th key={h} className="px-5 py-3.5 font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{students?.items.map((s) => <tr key={s.id}><td className="px-5 py-4"><Link href={`/students/${s.id}`} className="font-medium text-indigo-600">{s.name}</Link><p className="mt-1 text-[10px] text-slate-400">{s.student_no}</p></td><td className="px-5 py-4 text-slate-500">{s.gender} / {s.age} 岁</td><td className="px-5 py-4 text-slate-600">{s.education ?? "—"}<p className="mt-1 text-[10px] text-slate-400">{s.graduate_school}</p></td><td className="px-5 py-4 text-slate-500">{s.training_enrollment_date ?? "—"}</td><td className="px-5 py-4"><div className="flex gap-4 text-xs"><Link href={`/students/${s.id}`} className="text-indigo-500">学生详情</Link><button className="text-slate-500 hover:text-indigo-500" onClick={() => { setMoving(s); setTargetClass(""); }}>调整班级</button><Link href={`/scores?student_id=${s.id}&q=${encodeURIComponent(s.student_no)}`} className="text-slate-500 hover:text-indigo-500">考核成绩</Link></div></td></tr>)}{!students?.items.length && <EmptyState columns={5} title="该班级暂无学生" />}</tbody></table>
        : <table className="w-full whitespace-nowrap text-left text-[13px]"><thead className="bg-slate-50 text-[11px] text-slate-500"><tr>{["学生", "公司 / 岗位", "城市", "就业薪资", "操作"].map((h) => <th key={h} className="px-5 py-3.5 font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{employment?.items.map((r) => <tr key={r.id}><td className="px-5 py-4"><Link href={`/students/${r.student_id}`} className="font-medium text-indigo-600">{r.student_name_snapshot}</Link></td><td className="px-5 py-4 text-slate-600">{r.company_name}<p className="mt-1 text-[10px] text-slate-400">{r.position}</p></td><td className="px-5 py-4 text-slate-500">{r.employment_city}</td><td className="px-5 py-4 text-slate-600">¥ {displayMoney(r.salary_amount)} / {r.salary_period === "MONTH" ? "月" : "年"}</td><td className="px-5 py-4"><Link href={`/employment/${r.id}`} className="text-xs text-indigo-600">就业详情与薪资对比</Link></td></tr>)}{!employment?.items.length && <EmptyState columns={5} title="该班级暂无就业记录" />}</tbody></table>}</div>
      <div className="px-5 pb-5">{tab === "students" && students && <Pagination page={students.page} total={students.total} pageSize={students.page_size} onPage={loadStudents} />}{tab === "employment" && employment && <Pagination page={employment.page} total={employment.total} pageSize={employment.page_size} onPage={loadEmployment} />}</div>
    </section>
    <p className="mt-3 text-[10px] text-slate-400">及格率按未删除学生的有效成绩条数计算（≥60 / 总成绩数）。没有成绩时不展示 0% 以免误判。就业口径按历史班级快照。</p>
    {moving ? (
      <Dialog title={`调整班级 · ${moving.name}`} description={`学号 ${moving.student_no} · 当前班级 ${moving.class_no}`} onClose={() => setMoving(null)}>
        <Field label="目标班级">
          <select className={inputClass} value={targetClass} onChange={(e) => setTargetClass(e.target.value)}>
            <option value="">请选择目标班级</option>
            {allClasses.filter((c) => c.id !== moving.class_id).map((c) => <option key={c.id} value={c.id}>{c.class_no} · {c.class_name}（{c.class_status}）</option>)}
          </select>
        </Field>
        <p className="rounded-lg bg-indigo-50 p-3 text-xs leading-6 text-slate-500">转班只改学生的当前班级；历史成绩、就业快照仍按当时记录保留。</p>
        <div className="mt-6 flex justify-end gap-2"><Button tone="ghost" onClick={() => setMoving(null)}>取消</Button><Button disabled={!targetClass || busy} onClick={moveStudent}>{busy ? "保存中…" : "确认调整"}</Button></div>
      </Dialog>
    ) : null}
  </div>;
}
