"use client";
import Link from "next/link";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowUpRight, BookOpen, CalendarDays, ChevronRight, Filter, GraduationCap, Plus, RefreshCw, Search, Users } from "lucide-react";
import { api, type PageResult } from "@/lib/client";
import type { ClassItem, Student } from "@/lib/contracts";
import { loadOptions, queryString } from "@/lib/options";
import { Badge, Button, EmptyState, ErrorText, Field, inputClass, PageHeader, Pagination, StatCard } from "@/components/ui";
import { StudentForm } from "@/components/StudentForm";

const EMPTY = { q: "", class_id: "", gender: "", age_gt: "" };
export default function StudentsPage() { return <Suspense fallback={<p>正在加载学生档案…</p>}><StudentList /></Suspense>; }

function StudentList() {
  const params = useSearchParams();
  const [filters, setFilters] = useState(EMPTY); const [applied, setApplied] = useState(EMPTY);
  const [data, setData] = useState<PageResult<Student> | null>(null); const [classes, setClasses] = useState<ClassItem[]>([]);
  const [olderCount, setOlderCount] = useState(0);
  const [error, setError] = useState<string | null>(null); const [loading, setLoading] = useState(true); const [open, setOpen] = useState(false);
  async function load(values = applied, page = 1) {
    setLoading(true); setError(null);
    try {
      // 统计卡和列表用同一组筛选：30 岁以上人数也是当前条件内统计出来的
      const [pageData, age30] = await Promise.all([
        api<PageResult<Student>>(`/api/v1/students?${queryString({ ...values, page, page_size: 10 })}`),
        api<PageResult<Student>>(`/api/v1/students?${queryString({ ...values, age_gt: 30, page, page_size: 1 })}`),
      ]);
      setData(pageData); setOlderCount(age30.total);
    }
    catch (e) { setError(e instanceof Error ? e.message : "加载失败"); } finally { setLoading(false); }
  }
  async function metadata() {
    setClasses(await loadOptions<ClassItem>("/api/v1/classes"));
  }
  useEffect(() => {
    const next = { ...EMPTY, q: params.get("q") ?? "", class_id: params.get("class_id") ?? "", gender: params.get("gender") ?? "", age_gt: params.get("age_gt") ?? "" };
    setFilters(next); setApplied(next); void load(next);
    void metadata().catch((e) => setError(e instanceof Error ? e.message : "加载选项失败"));
  }, [params]);
  function search(event: FormEvent) { event.preventDefault(); setApplied(filters); void load(filters); }
  function reset() { setFilters(EMPTY); setApplied(EMPTY); void load(EMPTY); }
  async function remove(s: Student) {
    if (!confirm(`确定逻辑删除 ${s.name}（${s.student_no}）？成绩及就业历史会保留，但不再对普通查询显示。`)) return;
    try { await api(`/api/v1/students/${s.id}`, { method: "DELETE" }); await load(applied); await metadata(); }
    catch (e) { setError(e instanceof Error ? e.message : "删除失败"); }
  }
  return <div>
    <PageHeader title="学生档案" eyebrow="STUDENT MANAGEMENT" desc="从入学到就业，完整记录每一位学生的成长。" action={<Button onClick={() => setOpen(true)}><Plus size={16} />新增学生</Button>} />
    <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="在册学生" value={data?.total ?? "—"} icon={<Users size={21} />} description={applied.q || applied.class_id || applied.gender || applied.age_gt ? "当前筛选条件下的学生数" : "全部未删除学生"} />
      <StatCard label="培训班级" value={applied.class_id ? 1 : classes.length} icon={<BookOpen size={21} />} description={applied.class_id ? "当前选中班级" : "在读与历史班级"} />
      <StatCard label="30 岁以上" value={olderCount} icon={<CalendarDays size={21} />} description="当前条件内按出生日期动态计算" />
      <StatCard label="当前查询结果" value={data?.total ?? "—"} icon={<GraduationCap size={21} />} description="所有筛选条件共同生效" />
    </div>
    <section className="mb-5 rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-center gap-2 text-xs font-semibold text-slate-700"><Filter size={14} className="text-indigo-500" />筛选学生<span className="ml-auto text-[11px] font-normal text-slate-400">支持多条件组合查询</span></div>
      <form onSubmit={search}>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Field label="学号 / 姓名搜索"><div className="relative"><Search size={15} className="absolute left-3 top-3.5 text-slate-400" /><input className={`${inputClass} !pl-9`} placeholder="支持输入姓名或学号" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} /></div></Field>
          <Field label="班级筛选"><select className={inputClass} value={filters.class_id} onChange={(e) => setFilters({ ...filters, class_id: e.target.value })}><option value="">全部班级</option>{classes.map((c) => <option key={c.id} value={c.id}>{c.class_no} · {c.class_name}</option>)}</select></Field>
          <Field label="性别筛选"><select className={inputClass} value={filters.gender} onChange={(e) => setFilters({ ...filters, gender: e.target.value })}><option value="">全部性别</option><option>男</option><option>女</option><option>其他</option></select></Field>
          <Field label="年龄大于（> N 岁）"><input className={inputClass} type="number" min={0} max={150} step={1} placeholder="如输入 30 岁" value={filters.age_gt} onChange={(e) => setFilters({ ...filters, age_gt: e.target.value })} /></Field>
        </div><div className="mt-4 flex items-center gap-2"><Button type="submit" disabled={loading}><Search size={14} />查询</Button><Button tone="ghost" onClick={reset}>重置</Button><span className="ml-auto hidden text-[11px] text-slate-400 sm:block">出生日期实时计算年龄，不维护 age 字段</span></div>
      </form>
    </section>
    <ErrorText error={error} />
    <section className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between px-5 py-4"><div className="flex items-center gap-2"><h2 className="text-sm font-semibold text-slate-800">学生档案列表</h2><Badge tone="indigo">{data?.total ?? 0} 人</Badge></div><Button tone="ghost" onClick={() => load(applied, data?.page ?? 1)} className="!px-3 !py-2"><RefreshCw size={14} className={loading ? "animate-spin" : ""} />刷新</Button></div>
      <div className="overflow-x-auto"><table className="w-full whitespace-nowrap text-left text-[13px]"><thead className="border-y border-slate-100 bg-slate-50/80 text-[11px] text-slate-500"><tr>{["姓名 / 学号", "所属培训班级", "性别 / 年龄", "原学历与院校", "培训入学日期", "操作"].map((h) => <th key={h} className="px-5 py-3.5 font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">
        {data?.items.map((s, i) => <tr key={s.id} className="hover:bg-indigo-50/30"><td className="px-5 py-4"><Link href={`/students/${s.id}`} className="flex items-center gap-3"><span className={`grid h-9 w-9 place-items-center rounded-xl text-[11px] font-semibold ${["bg-indigo-50 text-indigo-500", "bg-rose-50 text-rose-500", "bg-sky-50 text-sky-500", "bg-amber-50 text-amber-600"][i % 4]}`}>{s.name.slice(-2)}</span><span><span className="block font-medium text-slate-800 hover:text-indigo-600">{s.name}</span><span className="mt-1 block text-[10px] text-slate-400">{s.student_no}</span></span></Link></td>
          <td className="px-5 py-4"><Link href={`/classes/${s.class_id}`} className="font-medium text-slate-600 hover:text-indigo-600">{s.class_no}</Link><span className="mt-1 block max-w-44 truncate text-[10px] text-slate-400">{s.class_name ?? "培训班级"}</span></td>
          <td className="px-5 py-4 text-slate-500">{s.gender}<span className="mx-2 text-slate-200">/</span>{s.age ?? "—"} 岁</td><td className="px-5 py-4 text-slate-600">{s.education ?? "未填写"}<span className="mt-1 block max-w-40 truncate text-[10px] text-slate-400">{s.graduate_school ?? "暂无院校信息"}</span></td><td className="px-5 py-4 text-slate-500">{s.training_enrollment_date ?? "—"}</td>
          <td className="px-5 py-4"><div className="flex items-center gap-4"><Link href={`/students/${s.id}`} className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600">查看详情<ArrowUpRight size={13} /></Link><button onClick={() => remove(s)} className="text-xs text-slate-400 hover:text-rose-500">删除</button></div></td></tr>)}
        {(!data || data.items.length === 0) && <EmptyState title={loading ? "正在查询学生档案…" : "没有匹配的学生"} columns={6} />}
      </tbody></table></div>
      <div className="px-5 pb-5">{data && <Pagination page={data.page} total={data.total} pageSize={data.page_size} onPage={(p) => load(applied, p)} />}</div>
    </section>
    {open && <StudentForm classes={classes} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); void load(applied); void metadata(); }} />}
  </div>;
}
