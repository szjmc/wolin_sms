"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Info } from "lucide-react";
import { api } from "@/lib/client";
import type { ClassItem, Relation, Teacher } from "@/lib/contracts";
import { Field, inputClass, Modal } from "@/components/ui";

export function ClassForm({ cls, teachers, relations, onClose, onSaved }: { cls?: ClassItem; teachers: Teacher[]; relations: Relation[]; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ class_no: cls?.class_no ?? "", class_name: cls?.class_name ?? "", start_date: cls?.start_date ?? "", completion_date: cls?.completion_date ?? "", class_status: cls?.class_status ?? "未开班", head_teacher_id: "", teacher_ids: [] as number[] });
  const [error, setError] = useState<string | null>(null); const [saving, setSaving] = useState(false);
  // 新版铁律：只要在未结课班级有任何有效关系，班主任和授课老师都不能再选这个人。
  function state(t: Teacher) {
    if (t.teacher_status !== "在职" || t.teaching_status !== "可授课") return `${t.teacher_status} / ${t.teaching_status}`;
    const busy = relations.find((r) => r.teacher_id === t.id && r.class_status !== "已结课");
    if (busy) return `已负责 ${busy.class_no}（${busy.relation_type}）`;
    return null;
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setError(null);
    if (!cls && (!form.head_teacher_id || !form.teacher_ids.length)) { setError("请指定班主任和至少一位任课老师"); return; }
    if (!cls && form.teacher_ids.includes(Number(form.head_teacher_id))) { setError("班主任和授课老师不能是同一人"); return; }
    setSaving(true);
    const payload = { ...(cls ? {} : { class_no: form.class_no, head_teacher_id: Number(form.head_teacher_id), teacher_ids: form.teacher_ids }), class_name: form.class_name, start_date: form.start_date, completion_date: form.completion_date || null, class_status: form.class_status };
    try { await api(cls ? `/api/v1/classes/${cls.id}` : "/api/v1/classes", { method: cls ? "PATCH" : "POST", body: JSON.stringify(payload) }); onSaved(); }
    catch (e) { setError(e instanceof Error ? e.message : "保存失败"); } finally { setSaving(false); }
  }
  return <Modal title={cls ? `编辑班级 · ${cls.class_no}` : "新增班级与教师安排"} onClose={onClose} onSubmit={save} error={error} saving={saving} wide>
    <div className="grid gap-4 sm:grid-cols-2"><Field label="班级编号 *"><input required disabled={!!cls} maxLength={30} className={inputClass} placeholder="如 WL2026-D" value={form.class_no} onChange={(e) => setForm({ ...form, class_no: e.target.value })} /></Field><Field label="班级名称 *"><input required maxLength={100} className={inputClass} placeholder="如 Python 全栈开发班" value={form.class_name} onChange={(e) => setForm({ ...form, class_name: e.target.value })} /></Field><Field label="开班日期 *"><input required type="date" className={inputClass} value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></Field><Field label="结课日期（选填）"><input type="date" className={inputClass} value={form.completion_date} onChange={(e) => setForm({ ...form, completion_date: e.target.value })} /></Field><Field label="班级状态"><select className={inputClass} value={form.class_status} onChange={(e) => setForm({ ...form, class_status: e.target.value })}><option>未开班</option><option>在读</option>{cls && <option>已结课</option>}</select></Field></div>
    {!cls ? <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4"><h3 className="mb-1 text-xs font-semibold text-indigo-600">指定班主任与任课老师</h3><p className="mb-4 flex items-start gap-1.5 text-[10px] leading-5 text-slate-400"><Info size={13} className="mt-0.5 shrink-0" />只可安排在职且可授课老师；一人只负责一个未结课班级；班主任与任课老师不能是同一人。姓名由 ID 关联读取，不重复手工存储。</p><Field label="班主任（姓名 / 编号 / ID） *"><select required className={inputClass} value={form.head_teacher_id} onChange={(e) => setForm({ ...form, head_teacher_id: e.target.value })}><option value="">请选择可分配的班主任</option>{teachers.map((t) => { const unavailable = state(t); return <option key={t.id} value={t.id} disabled={!!unavailable}>{t.name}（{t.teacher_no} · ID {t.id}）{unavailable ? ` · ${unavailable}` : " · 可分配"}</option>; })}</select></Field>
      <p className="mb-2 mt-4 text-xs text-slate-500">任课老师（可多选，不能与班主任同人） *</p><div className="grid max-h-52 gap-2 overflow-y-auto sm:grid-cols-2">{teachers.map((t) => { const unavailable = state(t) ?? (String(t.id) === form.head_teacher_id ? "已选为班主任" : null); return <label key={t.id} className={`flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 ${unavailable ? "opacity-45" : "cursor-pointer"}`}><input type="checkbox" disabled={!!unavailable} checked={form.teacher_ids.includes(t.id)} onChange={(e) => setForm({ ...form, teacher_ids: e.target.checked ? [...form.teacher_ids, t.id] : form.teacher_ids.filter((id) => id !== t.id) })} /><span><span className="block text-xs font-medium text-slate-600">{t.name} <span className="font-normal text-slate-400">{t.teacher_no} · ID {t.id}</span></span><span className="mt-1 block text-[10px] text-slate-400">{unavailable ?? t.specialty ?? "可授课"}</span></span></label>; })}</div></div>
      : <div className="rounded-lg bg-indigo-50 p-3 text-xs leading-6 text-indigo-600">教师安排请在<Link href={`/scheduling?class_id=${cls.id}`} className="mx-1 underline">班级排班与教师关系</Link>中维护。结课后关系保留为历史排班。</div>}
  </Modal>;
}
