"use client";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/client";
import type { ClassItem, Student } from "@/lib/contracts";
import { Field, inputClass, Modal } from "@/components/ui";

export function StudentForm({ student, classes, onClose, onSaved }: { student?: Student; classes: ClassItem[]; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ student_no: student?.student_no ?? "", name: student?.name ?? "", class_id: student?.class_id ? String(student.class_id) : "",
    gender: student?.gender ?? "男", birth_date: student?.birth_date ?? "", hometown: student?.hometown ?? "",
    graduate_school: student?.graduate_school ?? "", major: student?.major ?? "", education: student?.education ?? "本科",
    training_enrollment_date: student?.training_enrollment_date ?? "", training_graduation_date: student?.training_graduation_date ?? "", consultant_no: student?.consultant_no ?? "" });
  const [error, setError] = useState<string | null>(null); const [saving, setSaving] = useState(false);
  const change = (key: keyof typeof form, value: string) => setForm((old) => ({ ...old, [key]: value }));
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null);
    const payload = { ...(student ? {} : { student_no: form.student_no }), name: form.name, class_id: Number(form.class_id), gender: form.gender, birth_date: form.birth_date,
      hometown: form.hometown || null, graduate_school: form.graduate_school || null, major: form.major || null, education: form.education || null,
      training_enrollment_date: form.training_enrollment_date || null, training_graduation_date: form.training_graduation_date || null, consultant_no: form.consultant_no || null };
    try { await api(student ? `/api/v1/students/${student.id}` : "/api/v1/students", { method: student ? "PATCH" : "POST", body: JSON.stringify(payload) }); onSaved(); }
    catch (e) { setError(e instanceof Error ? e.message : "保存失败"); } finally { setSaving(false); }
  }
  return <Modal title={student ? `编辑档案 · ${student.name}` : "新增学生档案"} onClose={onClose} onSubmit={save} error={error} saving={saving} wide>
    <div className="grid gap-4 sm:grid-cols-2"><Field label="学号 *"><input className={inputClass} required disabled={!!student} maxLength={30} placeholder="如 ST20260009" value={form.student_no} onChange={(e) => change("student_no", e.target.value)} /></Field>
      <Field label="姓名 *"><input className={inputClass} required maxLength={50} placeholder="请输入姓名" value={form.name} onChange={(e) => change("name", e.target.value)} /></Field>
      <Field label="所属培训班级 *"><select className={inputClass} required value={form.class_id} onChange={(e) => change("class_id", e.target.value)}><option value="">请选择班级</option>{classes.map((c) => <option key={c.id} value={c.id}>{c.class_no} · {c.class_name}</option>)}</select></Field>
      <Field label="性别 *"><select className={inputClass} value={form.gender} onChange={(e) => change("gender", e.target.value)}><option>男</option><option>女</option><option>其他</option></select></Field>
      <Field label="出生日期 *" hint="仅保存出生日期，年龄自动计算"><input type="date" className={inputClass} max={new Date().toISOString().slice(0, 10)} required value={form.birth_date} onChange={(e) => change("birth_date", e.target.value)} /></Field>
      <Field label="籍贯"><input className={inputClass} value={form.hometown} onChange={(e) => change("hometown", e.target.value)} /></Field>
      <Field label="原毕业院校"><input className={inputClass} value={form.graduate_school} onChange={(e) => change("graduate_school", e.target.value)} /></Field>
      <Field label="原专业"><input className={inputClass} value={form.major} onChange={(e) => change("major", e.target.value)} /></Field>
      <Field label="原学历"><select className={inputClass} value={form.education} onChange={(e) => change("education", e.target.value)}><option>本科</option><option>大专</option><option>硕士</option><option>博士</option><option>高中</option><option>其他</option></select></Field>
      <Field label="顾问编号"><input className={inputClass} placeholder="选填" value={form.consultant_no} onChange={(e) => change("consultant_no", e.target.value)} /></Field>
      <Field label="培训入学日期"><input type="date" className={inputClass} value={form.training_enrollment_date} onChange={(e) => change("training_enrollment_date", e.target.value)} /></Field>
      <Field label="培训结课日期"><input type="date" className={inputClass} value={form.training_graduation_date} onChange={(e) => change("training_graduation_date", e.target.value)} /></Field>
    </div>
  </Modal>;
}
