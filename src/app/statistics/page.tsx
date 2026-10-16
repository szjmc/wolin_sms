"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertCircle, ArrowUpRight, CalendarDays, CheckCircle2, Info, RefreshCw, School, Users } from "lucide-react";
import { api, type PageResult } from "@/lib/client";
import { ErrorText, PageHeader } from "@/components/ui";

type PassStudent = { id: number; student_no: string; name: string; gender: string; birth_date: string; graduate_school: string | null; class_id: number; education: string | null; hometown: string | null; major: string | null };
type SeniorJobItem = { salary_amount: string; salary_period: string };
type FailItem = { student_id: number; student_no: string; name: string; class_id: number; class_no: string; class_name: string; fail_count: number };
type Avg = { class_id: number; class_no: string; class_name: string; exam_no: number; average_score: string; sample_count: number };
type Count = { class_id: number; class_no: string; class_name: string; total_students: number; male_count: number; female_count: number; other_count: number };
type Top = { rank: number; student_name_snapshot: string; company_name: string; position: string | null; education: string | null; salary_amount: string; salary_period: string; annualized_salary: string; class_no_snapshot: string };
type Duration = { class_no_snapshot: string; record_count: number; average_duration_days: string };
type ClassItem = { id: number; class_no: string; class_name: string };

// 本地算年龄：和后端口径一致（今年减出生年，生日没到减 1 岁）。
function ageOf(birth: string) {
  const [y, m, d] = birth.split("-").map(Number);
  const now = new Date();
  let age = now.getFullYear() - y;
  if (now.getMonth() + 1 < m || (now.getMonth() + 1 === m && now.getDate() < d)) age -= 1;
  return age;
}
function money(value: string | number) {
  return Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}
const rankStyle = ["bg-amber-400 text-white", "bg-slate-300 text-white", "bg-amber-700 text-white"];

export default function StatisticsPage() {
  const [pass, setPass] = useState<PassStudent[]>([]);
  const [fails, setFails] = useState<FailItem[]>([]);
  const [avgs, setAvgs] = useState<Avg[]>([]);
  const [counts, setCounts] = useState<Count[]>([]);
  const [top, setTop] = useState<Top[]>([]);
  const [durations, setDurations] = useState<Duration[]>([]);
  const [overAge, setOverAge] = useState<PassStudent[]>([]);
  const [seniorSalary, setSeniorSalary] = useState<{ count: number; avgAnnual: number; avgPastYears: number } | null>(null);
  const [classMap, setClassMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [passList, failList, avgList, countList, topList, durationList, overAgePage, classPage] = await Promise.all([
        api<PassStudent[]>("/api/v1/statistics/scores/all-at-least"),
        api<FailItem[]>("/api/v1/statistics/scores/failures"),
        api<Avg[]>("/api/v1/statistics/scores/class-averages"),
        api<Count[]>("/api/v1/statistics/classes/student-counts"),
        api<Top[]>("/api/v1/statistics/employment/top-salaries?limit=5"),
        api<Duration[]>("/api/v1/statistics/employment/class-average-durations"),
        api<PageResult<PassStudent>>("/api/v1/statistics/students/over-age?page_size=100"),
        api<PageResult<ClassItem>>("/api/v1/classes?page_size=100"),
      ]);
      setPass(passList);
      setFails(failList);
      setAvgs(avgList);
      setCounts(countList);
      setTop(topList);
      setDurations(durationList);
      setOverAge(overAgePage.items);
      const map: Record<number, string> = {};
      for (const c of classPage.items) map[c.id] = c.class_no;
      setClassMap(map);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { void load(); }, []);

  useEffect(() => {
    if (overAge.length === 0) { setSeniorSalary(null); return; }
    let cancelled = false;
    (async () => {
      try {
        const pages = await Promise.all(overAge.slice(0, 100).map((s) => api<PageResult<SeniorJobItem>>(`/api/v1/employment-records?student_no=${encodeURIComponent(s.student_no)}&page_size=100`)));
        let salarySum = 0; let recordCount = 0;
        for (const page of pages) for (const r of page.items) { const a = Number(r.salary_amount); salarySum += r.salary_period === "MONTH" ? a * 12 : a; recordCount += 1; }
        const avgAge = overAge.reduce((sum, s) => sum + ageOf(s.birth_date), 0) / overAge.length;
        if (!cancelled) setSeniorSalary({ count: recordCount, avgAnnual: recordCount ? salarySum / recordCount : 0, avgPastYears: avgAge });
      } catch { if (!cancelled) setSeniorSalary(null); }
    })();
    return () => { cancelled = true; };
  }, [overAge]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="统计分析"
        eyebrow="STATISTICS & INSIGHTS"
        desc="所有统计在查询层排除已逻辑删除的数据，只看有效学生和有效记录。"
        action={<button onClick={() => load()} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-[13px] font-medium text-slate-600 hover:bg-slate-50"><RefreshCw size={14} className={loading ? "animate-spin" : ""} />刷新数据</button>}
      />
      <ErrorText error={error} />
      {loading ? <p className="text-sm text-slate-400">正在统计全校数据…</p> : null}

      {/* 第一行：达标名单 + 不及格预警 */}
      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-[15px] font-semibold text-slate-800"><CheckCircle2 size={17} className="text-emerald-500" />考核成绩全达标名单</h2>
              <p className="mt-2 flex items-start gap-1 text-[11px] leading-5 text-emerald-600"><Info size={12} className="mt-0.5 shrink-0" />规则契约：至少 1 门有效成绩，且所有已录入成绩均 ≥ 80 分（无成绩或有 79 分均不计入）</p>
            </div>
            <span className="shrink-0 rounded-full bg-emerald-500 px-3 py-1.5 text-center text-[11px] font-semibold leading-4 text-white">达标：{pass.length}<br />人</span>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {pass.map((s) => (
              <Link key={s.id} href={`/students/${s.id}`} className="rounded-xl border border-emerald-100 bg-white p-4 transition hover:shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-800">{s.name}</span>
                  <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] text-emerald-600">{s.gender} · {ageOf(s.birth_date)}岁</span>
                </div>
                <p className="mt-2.5 text-[11px] text-slate-400">学号：{s.student_no} · 班级：{classMap[s.class_id] ?? "—"}</p>
                <p className="mt-1 text-[11px] text-slate-400">原毕业：{s.graduate_school ?? "未填写"}</p>
              </Link>
            ))}
          </div>
          {pass.length === 0 && !loading ? <p className="mt-4 text-center text-xs text-slate-400">暂无全部达标的学生</p> : null}
        </div>

        <div className="rounded-2xl border border-rose-100 bg-rose-50/60 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-[15px] font-semibold text-slate-800"><AlertCircle size={17} className="text-rose-500" />不及格重点帮扶预警</h2>
              <p className="mt-2 flex items-start gap-1 text-[11px] leading-5 text-rose-500"><Info size={12} className="mt-0.5 shrink-0" />规则契约：有效成绩中分数 &lt; 60 分的次数累计 ≥ 3 次的学员</p>
            </div>
            <span className="shrink-0 rounded-full bg-rose-500 px-3 py-1.5 text-center text-[11px] font-semibold leading-4 text-white">预警：{fails.length}<br />人</span>
          </div>
          <div className="mt-4 space-y-3">
            {fails.map((s) => (
              <Link key={s.student_id} href={`/students/${s.student_id}`} className="flex items-center justify-between rounded-xl border border-rose-100 bg-white p-4 transition hover:shadow-sm">
                <div>
                  <p className="text-sm font-semibold text-slate-800">{s.name} <span className="ml-1 text-[11px] font-normal text-slate-400">({s.student_no})</span></p>
                  <p className="mt-1.5 text-[11px] text-slate-400">所属班级：{s.class_name}</p>
                </div>
                <span className="rounded-md bg-rose-50 px-2.5 py-1 text-[11px] font-medium text-rose-500">不及格 {s.fail_count} 次</span>
              </Link>
            ))}
          </div>
          {fails.length === 0 && !loading ? <p className="mt-4 text-center text-xs text-slate-400">暂无需要预警的学员</p> : null}
        </div>
      </section>

      {/* 第二行：平均分 + 性别分布 */}
      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="flex items-center gap-2 text-[15px] font-semibold text-slate-800"><CalendarDays size={17} className="text-slate-400" />历次考试班级平均分统计</h2>
          <p className="mt-2 text-[11px] text-slate-400">排除已删除学员和已删除成绩记录</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {avgs.map((a) => (
              <div key={`${a.class_no}-${a.exam_no}`} className="rounded-xl bg-slate-50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-800">{a.class_no} 班</span>
                  <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-[10px] text-indigo-500">第 {a.exam_no} 次考核</span>
                </div>
                <p className="mt-3 text-2xl font-bold text-slate-900">{a.average_score}<span className="ml-1 text-xs font-normal text-slate-400">分（{a.sample_count}人次）</span></p>
              </div>
            ))}
          </div>
          {avgs.length === 0 && !loading ? <p className="mt-4 text-center text-xs text-slate-400">暂无考核成绩</p> : null}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="flex items-center gap-2 text-[15px] font-semibold text-slate-800"><Users size={17} className="text-slate-400" />班级在册学员与性别分布</h2>
          <p className="mt-2 text-[11px] text-slate-400">统计未删除学员性别比例</p>
          <div className="mt-4 space-y-3">
            {counts.map((c) => (
              <Link key={c.class_id} href={`/classes/${c.class_id}`} className="block rounded-xl bg-slate-50 p-4 transition hover:shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-[13px] font-semibold text-slate-800">{c.class_no} · {c.class_name}</span>
                  <span className="text-xs text-slate-500">总计 {c.total_students} 人</span>
                </div>
                <div className="mt-2.5 flex gap-2 text-[11px]">
                  <span className="rounded-md bg-sky-50 px-2 py-0.5 text-sky-600">男：{c.male_count}</span>
                  <span className="rounded-md bg-rose-50 px-2 py-0.5 text-rose-500">女：{c.female_count}</span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-500">其他：{c.other_count}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* 第三行：薪资榜 + 求职周期/年龄结构 */}
      <section className="grid items-start gap-6 xl:grid-cols-[1.65fr_1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-[15px] font-semibold text-slate-800"><School size={17} className="text-slate-400" />就业薪资龙虎榜 Top 5</h2>
              <p className="mt-2 text-[11px] text-slate-400">跨周期统一换算为年薪等价值排序（月薪 × 12），响应完整保留原月薪/年薪口径</p>
            </div>
            <Link href="/employment" className="inline-flex shrink-0 items-center gap-1 text-xs text-indigo-500">查看全部就业记录<ArrowUpRight size={13} /></Link>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full whitespace-nowrap text-left text-[13px]">
              <thead className="text-[11px] text-slate-400"><tr><th className="py-2 pr-4 font-medium">排名</th><th className="py-2 pr-4 font-medium">学员姓名</th><th className="py-2 pr-4 font-medium">就职企业 / 岗位</th><th className="py-2 pr-4 font-medium">学历</th><th className="py-2 pr-4 font-medium">原始薪资</th><th className="py-2 pr-4 font-medium">折算年薪等价值</th><th className="py-2 font-medium">班级快照</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {top.map((t) => (
                  <tr key={t.rank}>
                    <td className="py-3 pr-4"><span className={`grid h-6 w-6 place-items-center rounded-full text-[11px] font-bold ${rankStyle[t.rank - 1] ?? "bg-slate-100 text-slate-500"}`}>{t.rank}</span></td>
                    <td className="py-3 pr-4 font-medium text-slate-800">{t.student_name_snapshot}</td>
                    <td className="py-3 pr-4 text-slate-600">{t.company_name}<span className="block text-[11px] text-slate-400">{t.position ?? "岗位未填写"}</span></td>
                    <td className="py-3 pr-4 text-slate-500">{t.education ?? "—"}</td>
                    <td className="py-3 pr-4 font-medium text-slate-800">¥{money(t.salary_amount)}<span className="ml-1 text-[10px] font-normal text-slate-400">({t.salary_period === "MONTH" ? "月薪" : "年薪"})</span></td>
                    <td className="py-3 pr-4 font-semibold text-indigo-500">¥{money(t.annualized_salary)} / 年</td>
                    <td className="py-3 text-slate-400">{t.class_no_snapshot}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {top.length === 0 && !loading ? <p className="mt-4 text-center text-xs text-slate-400">暂无就业记录</p> : null}
        </div>

        <div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="flex items-center gap-2 text-[15px] font-semibold text-slate-800"><CalendarDays size={17} className="text-slate-400" />班级平均求职周期</h2>
            <p className="mt-2 text-[11px] text-slate-400">统计有效就业记录中具有开放与拿到 Offer 日期的自然日天数</p>
            <div className="mt-4 space-y-3">
              {durations.map((d) => (
                <div key={d.class_no_snapshot} className="flex items-center justify-between rounded-xl bg-slate-50 p-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-800">{d.class_no_snapshot} 班</p>
                    <p className="mt-1 text-[11px] text-slate-400">样本量：{d.record_count} 段有效就业</p>
                  </div>
                  <p className="text-lg font-bold text-indigo-500">{d.average_duration_days} 天</p>
                </div>
              ))}
            </div>
            {durations.length === 0 && !loading ? <p className="mt-4 text-center text-xs text-slate-400">暂无完整日期的就业记录</p> : null}
          </div>
        </div>
      </section>

      {/* 30 岁以上学员结构：两张等宽卡片，和上面各区块宽度统一 */}
      <section className="grid items-start gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-[15px] font-semibold text-slate-800">30 岁以上学员年龄结构</h2>
              <span className="rounded-full bg-indigo-500 px-3 py-1 text-[11px] font-semibold text-white">共 {overAge.length} 人</span>
            </div>
            <p className="mt-2 text-[11px] text-slate-400">年龄由出生日期动态计算，不单独维护</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {overAge.map((s) => (
                <Link key={s.id} href={`/students/${s.id}`} className="rounded-lg bg-white px-3 py-1.5 text-xs text-slate-600 ring-1 ring-indigo-100 hover:text-indigo-600">{s.name}（{ageOf(s.birth_date)}岁）</Link>
              ))}
            </div>
            {overAge.length === 0 && !loading ? <p className="mt-4 text-center text-xs text-slate-400">暂无 30 岁以上学员</p> : null}
          </div>

          <div className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-[15px] font-semibold text-slate-800">30 岁以上学员画像</h2>
              <span className="rounded-full bg-emerald-500 px-3 py-1 text-[11px] font-semibold text-white">学历年限分布</span>
            </div>
            <p className="mt-2 text-[11px] text-slate-400">学历与平均年龄、毕业后就业薪资一起看（样本 ≤ 100 人）</p>
            <div className="mt-4 space-y-2">
              {Object.entries(overAge.reduce<Record<string, { n: number; age: number }>>((acc, s) => {
                const key = s.education ?? "未填写";
                if (!acc[key]) acc[key] = { n: 0, age: 0 };
                acc[key].n += 1; acc[key].age += ageOf(s.birth_date);
                return acc;
              }, {})).map(([edu, stat]) => (
                <div key={edu} className="flex items-center justify-between rounded-xl bg-white p-3 text-xs ring-1 ring-emerald-100">
                  <span className="font-medium text-slate-700">{edu}</span>
                  <span className="text-slate-400">{stat.n} 人 · 占 {(stat.n * 100 / Math.max(overAge.length, 1)).toFixed(0)}% · 平均 {(stat.age / stat.n).toFixed(1)} 岁</span>
                </div>
              ))}
              {overAge.length === 0 && !loading ? <p className="text-center text-xs text-slate-400">暂无大龄学员样本</p> : null}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-center">
              <div className="rounded-xl bg-white p-4 ring-1 ring-emerald-100"><p className="text-[10px] text-slate-400">大龄学员平均年龄</p><p className="mt-1.5 text-lg font-bold text-emerald-600">{seniorSalary ? `${seniorSalary.avgPastYears.toFixed(1)} 岁` : "—"}</p></div>
              <div className="rounded-xl bg-white p-4 ring-1 ring-emerald-100"><p className="text-[10px] text-slate-400">平均年薪等价值{seniorSalary ? `（${seniorSalary.count} 条就业）` : ""}</p><p className="mt-1.5 text-lg font-bold text-emerald-600">{seniorSalary && seniorSalary.count ? `¥${money(Math.round(seniorSalary.avgAnnual))}` : "暂无就业"}</p></div>
            </div>
            <p className="mt-3 text-[10px] leading-5 text-slate-400">平均年龄只统计 30 岁以上学员；平均薪资按其有效就业记录折算成年薪（月薪 × 12）。最高学历分布来自学生档案的 education 字段。</p>
          </div>
      </section>
    </div>
  );
}
