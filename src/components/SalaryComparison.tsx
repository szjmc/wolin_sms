"use client";
import { useEffect, useState } from "react";
import { ArrowRight, ArrowUpRight, BriefcaseBusiness, TrendingDown, TrendingUp } from "lucide-react";
import { api } from "@/lib/client";
import type { SalaryComparison } from "@/lib/contracts";
import { displayMoney } from "@/lib/options";
import { ErrorText } from "@/components/ui";

export function SalaryComparisonPanel({ recordId }: { recordId: number }) {
  const [data, setData] = useState<SalaryComparison | null>(null); const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false; setData(null); setError(null);
    void api<SalaryComparison>(`/api/v1/employment-records/${recordId}/comparison`).then((result) => { if (!cancelled) setData(result); }).catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [recordId]);
  if (error) return <ErrorText error={error} />;
  if (!data) return <div className="py-10 text-center text-sm text-slate-400">正在计算薪资对比…</div>;
  const positive = data.annual_increase !== null && Number(data.annual_increase) >= 0;
  const beforeHeight = data.past_annualized_salary === null ? 0 : Math.max(8, Number(data.past_annualized_salary) / Math.max(Number(data.annualized_salary), Number(data.past_annualized_salary), 1) * 120);
  const afterHeight = Math.max(8, Number(data.annualized_salary) / Math.max(Number(data.annualized_salary), Number(data.past_annualized_salary ?? 0), 1) * 120);
  return <div>
    <div className="grid gap-4 sm:grid-cols-2"><div className="rounded-xl border border-slate-200 bg-slate-50 p-5"><p className="flex items-center gap-2 text-xs text-slate-500"><BriefcaseBusiness size={14} />培训前 · 以往就业</p><p className="mt-4 text-base font-semibold text-slate-700">{data.previous_position || "以往岗位未填写"}</p><p className="mt-3 text-2xl font-semibold text-slate-800">{data.past_salary_amount === null ? "暂无薪资" : `¥ ${displayMoney(data.past_salary_amount)}`}</p><p className="mt-1 text-xs text-slate-400">{data.past_salary_period ? data.past_salary_period === "MONTH" ? "原始月薪" : "原始年薪" : "尚无历史薪资基准"}</p></div>
      <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-5"><p className="flex items-center gap-2 text-xs text-indigo-500"><ArrowUpRight size={14} />培训后 · 本次就业</p><p className="mt-4 text-base font-semibold text-indigo-700">{data.position || "岗位未填写"}</p><p className="mt-3 text-2xl font-semibold text-indigo-600">¥ {displayMoney(data.salary_amount)}</p><p className="mt-1 text-xs text-indigo-400">{data.salary_period === "MONTH" ? "原始月薪" : "原始年薪"}</p></div></div>
    <div className="mt-5 rounded-xl border border-slate-100 p-5"><div className="flex items-center justify-between"><h3 className="text-sm font-medium text-slate-700">统一口径对比</h3><span className="text-[10px] text-slate-400">金额均折算成年薪</span></div>
      <div className="mt-5 grid gap-6 sm:grid-cols-[1fr_160px]"><div className="grid content-center gap-3"><div className="flex justify-between text-xs"><span className="text-slate-400">以前年薪等值</span><span className="font-medium text-slate-600">{data.past_annualized_salary === null ? "暂无基准" : `¥ ${displayMoney(data.past_annualized_salary)}`}</span></div><div className="flex justify-between text-xs"><span className="text-slate-400">本次年薪等值</span><span className="font-medium text-indigo-600">¥ {displayMoney(data.annualized_salary)}</span></div><div className="flex justify-between text-xs"><span className="text-slate-400">折合月薪</span><span className="inline-flex items-center gap-1.5 text-slate-600">{displayMoney(data.monthly_before)}<ArrowRight size={11} />{displayMoney(data.monthly_after)}</span></div></div>
        <div className="flex h-36 items-end justify-center gap-7 border-b border-slate-200 pb-5"><div className="relative w-10 rounded-t-md bg-slate-200" style={{ height: beforeHeight }}><span className="absolute -bottom-5 left-0 w-full text-center text-[9px] text-slate-400">以前</span></div><div className="relative w-10 rounded-t-md bg-indigo-500" style={{ height: afterHeight }}><span className="absolute -bottom-5 left-0 w-full text-center text-[9px] text-slate-400">就业后</span></div></div>
      </div></div>
    <div className={`mt-5 flex items-center justify-between rounded-xl p-4 ${!data.comparison_available ? "bg-slate-50" : positive ? "bg-emerald-50" : "bg-rose-50"}`}><div className="flex items-center gap-2"><span className={positive ? "text-emerald-500" : "text-rose-500"}>{positive ? <TrendingUp size={19} /> : <TrendingDown size={19} />}</span><span className="text-xs text-slate-600">{data.comparison_available ? "年薪变化" : "缺少以往薪资，暂不能计算变化"}</span></div>{data.comparison_available && <div className="text-right"><span className={`text-lg font-semibold ${positive ? "text-emerald-600" : "text-rose-600"}`}>{positive ? "+" : ""}¥ {displayMoney(data.annual_increase)}</span><p className="mt-0.5 text-[10px] text-slate-500">{data.increase_percent !== null ? `${Number(data.increase_percent) >= 0 ? "+" : ""}${data.increase_percent}%` : "以往薪资为零，不计算百分比"}</p></div>}</div>
    <p className="mt-4 text-[10px] leading-5 text-slate-400">以往薪资与岗位是本次就业记录的历史快照。月薪 × 12 = 年薪等值，原始薪资金额不会被覆盖。</p>
  </div>;
}
