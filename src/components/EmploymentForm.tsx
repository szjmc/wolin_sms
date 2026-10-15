"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/client";
import type { Employment, PastExperience, Student } from "@/lib/contracts";
import { loadOptions } from "@/lib/options";
import { Field, inputClass, Modal } from "@/components/ui";

export function EmploymentForm({ record, students, initialStudentId, onClose, onSaved }: { record?: Employment; students: Student[]; initialStudentId?: number; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ student_id: String(record?.student_id ?? initialStudentId ?? ""), company_name: record?.company_name ?? "", employment_city: record?.employment_city ?? "", position: record?.position ?? "", salary_amount: record?.salary_amount ?? "", salary_period: record?.salary_period ?? "MONTH", employment_open_date: record?.employment_open_date ?? "", offer_date: record?.offer_date ?? "", previous_position: record?.previous_position ?? "", past_salary_amount: record?.past_salary_amount ?? "", past_salary_period: record?.past_salary_period ?? "MONTH", past_graduation_date: record?.past_graduation_date ?? "" });
  const [saving, setSaving] = useState(false); const [loadingPast, setLoadingPast] = useState(false); const [error, setError] = useState<string | null>(null);
  const change = (key: keyof typeof form, value: string) => setForm((old) => ({ ...old, [key]: value }));
  useEffect(() => {
    if (record || !form.student_id) return;
    let cancelled = false; setLoadingPast(true);
    void loadOptions<PastExperience>(`/api/v1/students/${form.student_id}/past-experiences`).then((items) => {
      if (cancelled) return; const latest = [...items].sort((a, b) => b.id - a.id)[0];
      setForm((old) => ({ ...old, previous_position: latest?.previous_position ?? "", past_salary_amount: latest?.past_salary_amount ?? "", past_salary_period: latest?.past_salary_period ?? "MONTH", past_graduation_date: latest?.graduation_date ?? "" }));
    }).catch((e) => { if (!cancelled) setError(e.message); }).finally(() => { if (!cancelled) setLoadingPast(false); });
    return () => { cancelled = true; };
  }, [form.student_id, record]);
  const openDate = form.employment_open_date; const offerDate = form.offer_date;
  // 就業還没開放就不能填 Offer；Offer 日期不能早く就業開日（前端實時攔截、保存再兜底）
  const offerError = offerDate && !openDate ? "就业尚未开放，填写 Offer 日期之前请先填写就业开放日期" : offerDate && openDate && offerDate < openDate ? `Offer 日期（${offerDate}）不能早于就业开放日期（${openDate}），请先修改任一日期` : null;
  async function save(event: FormEvent) {
    event.preventDefault(); if (loadingPast) return; setError(null);
    if (offerError) { setError(offerError); return; }
    setSaving(true);
    const payload = { ...(record ? {} : { student_id: Number(form.student_id) }), company_name: form.company_name, employment_city: form.employment_city || null, position: form.position || null, salary_amount: form.salary_amount, salary_period: form.salary_period, employment_open_date: form.employment_open_date || null, offer_date: form.offer_date || null, previous_position: form.previous_position || null, past_salary_amount: form.past_salary_amount === "" ? null : form.past_salary_amount, past_salary_period: form.past_salary_amount === "" ? null : form.past_salary_period, past_graduation_date: form.past_graduation_date || null };
    try { await api(record ? `/api/v1/employment-records/${record.id}` : "/api/v1/employment-records", { method: record ? "PATCH" : "POST", body: JSON.stringify(payload) }); onSaved(); }
    catch (e) { setError(e instanceof Error ? e.message : "保存失败"); } finally { setSaving(false); }
  }
  return <Modal title={record ? "编辑就业记录" : "新增就业记录"} wide error={error} saving={saving || loadingPast} onClose={onClose} onSubmit={save}>
    <Field label="学生 *"><select required className={inputClass} disabled={!!record} value={form.student_id} onChange={(e) => change("student_id", e.target.value)}><option value="">请选择学生</option>{students.map((s) => <option key={s.id} value={s.id}>{s.name}（{s.student_no}）</option>)}</select></Field>
    <div className="grid gap-4 sm:grid-cols-2"><Field label="就业公司 *"><input required className={inputClass} value={form.company_name} onChange={(e) => change("company_name", e.target.value)} /></Field><Field label="工作城市"><input className={inputClass} value={form.employment_city} onChange={(e) => change("employment_city", e.target.value)} /></Field><Field label="就业岗位"><input className={inputClass} value={form.position} onChange={(e) => change("position", e.target.value)} /></Field><Field label="薪资周期 *"><select className={inputClass} value={form.salary_period} onChange={(e) => change("salary_period", e.target.value)}><option value="MONTH">月薪 MONTH</option><option value="YEAR">年薪 YEAR</option></select></Field><Field label="薪资金额 *"><input required type="number" min={0} step="0.01" className={inputClass} value={form.salary_amount} onChange={(e) => change("salary_amount", e.target.value)} /></Field><Field label="就业开放日期"><input type="date" className={inputClass} max={form.offer_date || undefined} value={form.employment_open_date} onChange={(e) => change("employment_open_date", e.target.value)} /></Field><Field label="Offer 日期"><input type="date" className={inputClass} min={form.employment_open_date || undefined} value={form.offer_date} onChange={(e) => change("offer_date", e.target.value)} /></Field></div>
      {offerError ? <p className="-mt-1 rounded-lg bg-rose-50 p-3 text-xs leading-5 text-rose-600">⚠ {offerError}</p> : <p className="-mt-1 text-[10px] leading-5 text-slate-400">先開放就業服務再有 Offer；Offer 日期最早只能和開放日期同一天。</p>}
    <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4"><h3 className="mb-1 text-xs font-semibold text-indigo-600">就业前信息 · 历史快照</h3><p className="mb-4 text-[10px] leading-5 text-slate-400">{loadingPast ? "正在读取过往经历…" : "新增时自动读取该学生最近一条有效过往经历，也可手动补充。毕业日期是原学历毕业日期，不是培训结课日期。"}</p><div className="grid gap-4 sm:grid-cols-2"><Field label="以往岗位"><input className={inputClass} value={form.previous_position} onChange={(e) => change("previous_position", e.target.value)} /></Field><Field label="以往薪资周期"><select className={inputClass} value={form.past_salary_period} onChange={(e) => change("past_salary_period", e.target.value)}><option value="MONTH">月薪 MONTH</option><option value="YEAR">年薪 YEAR</option></select></Field><Field label="以往薪资（选填）"><input type="number" min={0} step="0.01" className={inputClass} value={form.past_salary_amount} onChange={(e) => change("past_salary_amount", e.target.value)} /></Field><Field label="原学历毕业日期"><input type="date" className={inputClass} max={new Date().toISOString().slice(0, 10)} value={form.past_graduation_date} onChange={(e) => change("past_graduation_date", e.target.value)} /></Field></div></div>
  </Modal>;
}
