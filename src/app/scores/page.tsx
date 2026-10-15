"use client";
import Link from "next/link";
import { Suspense, useEffect, useRef, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowDownToLine, ArrowUpFromLine, BookOpenCheck, CheckCheck, FileSpreadsheet, Filter, Info, PencilLine, Plus, RefreshCw, RotateCcw, Save, Search, ShieldCheck, Trash2, TrendingUp } from "lucide-react";
import { api, type PageResult } from "@/lib/client";
import type { ClassItem, Score, ScoreSummary, Student } from "@/lib/contracts";
import { loadOptions, queryString } from "@/lib/options";
import { Badge, Button, EmptyState, ErrorText, Field, inputClass, Modal, PageHeader, Pagination, StatCard, SuccessText } from "@/components/ui";

type FoundScore = Pick<Score, "student_id" | "exam_no" | "score" | "updated_at">;
const EMPTY_FILTERS = { q: "", class_id: "", exam_no: "", score_band: "", min_score: "", max_score: "", sort: "latest" };
export default function ScoresPage() { return <Suspense fallback={<p>正在加载考核管理…</p>}><ScoreManager /></Suspense>; }

function ScoreManager() {
  const params = useSearchParams();
  const [students, setStudents] = useState<Student[]>([]); const [classes, setClasses] = useState<ClassItem[]>([]); const [exams, setExams] = useState<number[]>([]);
  const [studentId, setStudentId] = useState(""); const [examNo, setExamNo] = useState("1"); const [value, setValue] = useState(""); const [found, setFound] = useState<FoundScore | null>(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS); const [data, setData] = useState<PageResult<Score> | null>(null); const [summary, setSummary] = useState<ScoreSummary | null>(null);
  const [error, setError] = useState<string | null>(null); const [message, setMessage] = useState<string | null>(null); const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(false);
  const [newOpen, setNewOpen] = useState(false); const [newForm, setNewForm] = useState({ student_id: "", exam_no: "1", score: "80" }); const [modalError, setModalError] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]); const fileRef = useRef<HTMLInputElement>(null); const requestId = useRef(0);
  const isCurrent = !!found && String(found.student_id) === studentId && String(found.exam_no) === examNo;
  async function load(values = filters, page = 1) {
    const id = ++requestId.current; setLoading(true);
    const q = queryString({ ...values, page, page_size: 10 });
    try {
      const [table, stat, choices] = await Promise.all([api<PageResult<Score>>(`/api/v1/scores?${q}`), api<ScoreSummary>(`/api/v1/scores/summary?${q}`), api<number[]>("/api/v1/scores/exams")]);
      if (id !== requestId.current) return; setData(table); setSummary(stat); setExams(choices); setSelectedKeys([]);
    } catch (e) { if (id === requestId.current) setError(e instanceof Error ? e.message : "加载失败"); }
    finally { if (id === requestId.current) setLoading(false); }
  }
  useEffect(() => {
    void Promise.all([loadOptions<Student>("/api/v1/students"), loadOptions<ClassItem>("/api/v1/classes")]).then(([s, c]) => { setStudents(s); setClasses(c); }).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    const sid = params.get("student_id") ?? ""; setStudentId(sid); setFound(null); setValue("");
    setFilters({ ...EMPTY_FILTERS, class_id: params.get("class_id") ?? "", q: params.get("q") ?? "" });
  }, [params]);
  useEffect(() => { const timer = setTimeout(() => { void load(filters); }, 250); return () => clearTimeout(timer); }, [filters]);
  function identify(key: "student" | "exam", next: string) { if (key === "student") setStudentId(next); else setExamNo(next); setFound(null); setValue(""); setMessage(null); setError(null); }
  async function query(event?: FormEvent) {
    event?.preventDefault(); if (!studentId || !/^\d+$/.test(examNo) || Number(examNo) < 1) { setError("请先选择学生，并输入正整数考试序次"); return; }
    setBusy(true); setError(null); setMessage(null);
    try { const row = await api<FoundScore>(`/api/v1/students/${studentId}/scores/${examNo}`); setFound(row); setValue(row.score); setMessage(`已查询：第 ${row.exam_no} 次考试，${row.score} 分。可以修改当前分数。`); }
    catch (e) { setFound(null); setValue(""); setError(e instanceof Error ? e.message : "查询失败"); } finally { setBusy(false); }
  }
  async function save() {
    if (!isCurrent) return;
    if (value === "" || !Number.isFinite(Number(value)) || Number(value) < 0 || Number(value) > 100) { setError("请输入 0–100 的分数"); return; }
    setBusy(true); setError(null); setMessage(null);
    try { const row = await api<FoundScore>(`/api/v1/students/${studentId}/scores/${examNo}`, { method: "PATCH", body: JSON.stringify({ score: value }) }); setFound(row); setValue(row.score); setMessage(`已保存：第 ${row.exam_no} 次考试，${row.score} 分`); await load(filters, data?.page ?? 1); }
    catch (e) { setError(e instanceof Error ? e.message : "修改失败"); } finally { setBusy(false); }
  }
  async function remove(sid: number, exam: number, name?: string) {
    if (!confirm(`确定删除${name ?? "该学生"}第 ${exam} 次考核成绩？删除后可重新录入。`)) return;
    setBusy(true); setError(null);
    try { await api(`/api/v1/students/${sid}/scores/${exam}`, { method: "DELETE" }); if (studentId === String(sid) && examNo === String(exam)) { setFound(null); setValue(""); } setMessage(`已删除第 ${exam} 次成绩，历史记录保留`); await load(filters); }
    catch (e) { setError(e instanceof Error ? e.message : "删除失败"); } finally { setBusy(false); }
  }
  function resetCore() { setStudentId(""); setExamNo("1"); setValue(""); setFound(null); setMessage(null); setError(null); }
  const [editRow, setEditRow] = useState<Score | null>(null); const [editValue, setEditValue] = useState(""); const [editError, setEditError] = useState<string | null>(null);
  function quickEdit(row: Score) { setEditRow(row); setEditValue(row.score); setEditError(null); }
  async function saveEdit(event: FormEvent) {
    event.preventDefault(); if (!editRow) return;
    const value = Number(editValue);
    if (editValue.trim() === "" || !Number.isFinite(value) || value < 0 || value > 100) { setEditError("分数范围是 0–100"); return; }
    setBusy(true);
    try {
      await api(`/api/v1/students/${editRow.student_id}/scores/${editRow.exam_no}`, { method: "PATCH", body: JSON.stringify({ score: editValue }) });
      setMessage(`已修改 ${editRow.name} 第 ${editRow.exam_no} 次成绩为 ${editValue} 分`); setEditRow(null); await load(filters, data?.page ?? 1);
    } catch (e) { setEditError(e instanceof Error ? e.message : "修改失败"); } finally { setBusy(false); }
  }
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setModalError(null);
    try { const row = await api<FoundScore>("/api/v1/scores", { method: "POST", body: JSON.stringify({ student_id: Number(newForm.student_id), exam_no: Number(newForm.exam_no), score: newForm.score }) }); setNewOpen(false); setStudentId(String(row.student_id)); setExamNo(String(row.exam_no)); setValue(row.score); setFound(row); setMessage(`已录入新成绩：第 ${row.exam_no} 次，${row.score} 分`); await load(filters); }
    catch (e) { setModalError(e instanceof Error ? e.message : "录入失败"); } finally { setBusy(false); }
  }
  async function exportExcel(template = false) {
    setError(null); setBusy(true);
    try { const query = queryString({ ...filters, ...(selectedKeys.length ? { keys: selectedKeys.join(",") } : {}) });
      const response = await fetch(`/api/v1/scores/${template ? "template" : "export"}?${query}`);
      if (!response.ok) { const body = await response.json(); throw new Error(body.message || "导出失败"); }
      const url = URL.createObjectURL(await response.blob()); const a = document.createElement("a"); a.href = url; a.download = template ? "成绩导入模板.xlsx" : `考试成绩_${new Date().toISOString().slice(0, 10)}.xlsx`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      if (!template) setMessage(selectedKeys.length ? `已导出 ${selectedKeys.length} 条选中成绩` : "已导出当前筛选条件下的全部成绩（不限当前页）");
    } catch (e) { setError(e instanceof Error ? e.message : "导出失败"); } finally { setBusy(false); }
  }
  async function importExcel(file?: File) {
    if (!file) return; setBusy(true); setError(null); setMessage(null);
    try { const form = new FormData(); form.append("file", file); const result = await api<{ imported: number }>("/api/v1/scores/import", { method: "POST", body: form }); setMessage(`成功导入 ${result.imported} 条成绩`); await load(filters); }
    catch (e) { setError(e instanceof Error ? e.message : "导入失败"); } finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  }
  const visibleKeys = data?.items.map((r) => `${r.student_id}:${r.exam_no}`) ?? [];
  return <div>
    <PageHeader title="考核成绩管理" eyebrow="EXAMINATION & ASSESSMENT" desc="按学生与考试序次精确操作，所有有效成绩统一管理。" action={<Button onClick={() => { setNewForm({ student_id: studentId, exam_no: examNo, score: "80" }); setModalError(null); setNewOpen(true); }}><Plus size={16} />录入新成绩</Button>} />
    <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label="有效成绩记录" value={summary?.total ?? "—"} icon={<BookOpenCheck size={20} />} /><StatCard label="平均分" value={summary?.average_score ?? "—"} icon={<TrendingUp size={20} />} /><StatCard label="及格成绩 ≥ 60" value={summary?.pass_count ?? "—"} icon={<ShieldCheck size={20} />} /><StatCard label="优秀成绩 ≥ 80" value={summary?.excellent_count ?? "—"} icon={<CheckCheck size={20} />} /></div>
    <section id="score-core" className="mb-6 scroll-mt-24 rounded-xl border border-indigo-200 bg-white p-5">
      <div className="mb-2 flex flex-wrap items-center gap-2"><h2 className="text-sm font-semibold text-slate-800">按「学生 + 考核序次」查改删成绩</h2><Badge tone="indigo">核心业务操作</Badge></div><p className="mb-5 flex items-center gap-1.5 text-[11px] text-slate-400"><Info size={13} />只操作所选学生的指定考试，不需要成绩主键 score_id。</p>
      <form onSubmit={query}><div className="grid gap-3 md:grid-cols-3">{[
        { n: "01", label: "选择学生", element: <select className={inputClass} value={studentId} onChange={(e) => identify("student", e.target.value)}><option value="">请选择学生</option>{students.map((s) => <option key={s.id} value={s.id}>{s.name}（{s.student_no}）</option>)}</select> },
        { n: "02", label: "考核序次", element: <input className={inputClass} type="number" min={1} step={1} value={examNo} onChange={(e) => identify("exam", e.target.value)} /> },
        { n: "03", label: "当前分数（可编辑）", element: <input className={inputClass} type="number" min={0} max={100} step="0.01" disabled={!isCurrent} placeholder="先查询，再修改分数" value={value} onChange={(e) => setValue(e.target.value)} /> },
      ].map((box) => <div key={box.n} className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-4"><div className="mb-3 flex items-center gap-2"><span className="grid h-5 w-5 place-items-center rounded-full bg-indigo-100 text-[9px] font-bold text-indigo-600">{box.n}</span><span className="text-xs font-medium text-slate-600">{box.label}</span></div>{box.element}</div>)}</div>
        <div className="mt-5"><ErrorText error={error} /><SuccessText message={message} /></div>
        {found && <p className="mb-4 text-[11px] text-slate-400">最后更新：{new Date(found.updated_at).toLocaleString("zh-CN")}</p>}
        <div className="flex flex-wrap gap-2"><Button type="submit" disabled={busy}><Search size={14} />查询</Button><Button tone="success" disabled={!isCurrent || busy} onClick={save}><Save size={14} />保存修改</Button><Button tone="danger" disabled={!isCurrent || busy} onClick={() => remove(Number(studentId), Number(examNo))}><Trash2 size={14} />删除该次</Button><Button tone="ghost" onClick={resetCore}><RotateCcw size={14} />重置</Button></div>
      </form>
    </section>
    <section className="rounded-xl border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"><div className="flex items-center gap-2"><FileSpreadsheet size={17} className="text-indigo-500" /><h2 className="text-sm font-semibold">全员考试成绩大表</h2><Badge tone="indigo">{data?.total ?? 0} 条</Badge></div><div className="flex flex-wrap gap-2"><Button tone="ghost" disabled={busy} className="!px-3 !py-2" onClick={() => exportExcel(true)}>下载模板</Button><Button tone="ghost" disabled={busy} className="!px-3 !py-2" onClick={() => fileRef.current?.click()}><ArrowUpFromLine size={14} />导入 Excel</Button><Button tone="ghost" disabled={busy} className="!px-3 !py-2" onClick={() => exportExcel()}><ArrowDownToLine size={14} />导出 Excel</Button><Button tone="ghost" className="!px-3 !py-2" onClick={() => load(filters, data?.page ?? 1)}><RefreshCw size={14} className={loading ? "animate-spin" : ""} />刷新</Button><input ref={fileRef} type="file" accept=".xlsx" className="hidden" onChange={(e) => importExcel(e.target.files?.[0])} /></div></div>
      <div className="grid gap-3 border-t border-slate-100 bg-slate-50/40 px-5 py-4 sm:grid-cols-2 xl:grid-cols-5"><Field label="姓名 / 学号"><input className={inputClass} placeholder="搜索姓名或学号" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} /></Field><Field label="所属班级"><select className={inputClass} value={filters.class_id} onChange={(e) => setFilters({ ...filters, class_id: e.target.value })}><option value="">全部班级</option>{classes.map((c) => <option key={c.id} value={c.id}>{c.class_no}</option>)}</select></Field><Field label="考试序次"><select className={inputClass} value={filters.exam_no} onChange={(e) => setFilters({ ...filters, exam_no: e.target.value })}><option value="">全部序次</option>{exams.map((n) => <option key={n} value={n}>第 {n} 次</option>)}</select></Field><Field label="分数段"><select className={inputClass} value={filters.score_band} onChange={(e) => setFilters({ ...filters, score_band: e.target.value })}><option value="">全部分数</option><option value="excellent">优秀（≥ 80）</option><option value="pass">及格（60–79.99）</option><option value="fail">{"不及格（< 60）"}</option></select></Field><Field label="排序"><select className={inputClass} value={filters.sort} onChange={(e) => setFilters({ ...filters, sort: e.target.value })}><option value="latest">最近更新</option><option value="score_desc">分数从高到低</option><option value="score_asc">分数从低到高</option><option value="exam_asc">按考试序次</option></select></Field></div>
      <div className="flex flex-wrap items-center gap-3 px-5 pb-4 pt-2 text-xs text-slate-400"><span>自定义分数区间</span><input className={`${inputClass} !h-8 !w-24`} type="number" min={0} max={100} placeholder="最低分" value={filters.min_score} onChange={(e) => setFilters({ ...filters, min_score: e.target.value, score_band: "" })} /><span>至</span><input className={`${inputClass} !h-8 !w-24`} type="number" min={0} max={100} placeholder="最高分" value={filters.max_score} onChange={(e) => setFilters({ ...filters, max_score: e.target.value, score_band: "" })} /><button className="ml-auto text-indigo-500" onClick={() => setFilters(EMPTY_FILTERS)}>清空筛选</button></div>
      <div className="overflow-x-auto"><table className="w-full whitespace-nowrap text-left text-[13px]"><thead className="border-y border-slate-100 bg-slate-50 text-[11px] text-slate-500"><tr><th className="px-5 py-3"><input type="checkbox" aria-label="选择本页全部成绩" checked={visibleKeys.length > 0 && selectedKeys.length === visibleKeys.length} onChange={(e) => setSelectedKeys(e.target.checked ? visibleKeys : [])} /></th>{["姓名 / 学号", "所属班级", "考试序次", "分数值", "评定等级", "快捷操作"].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{data?.items.map((r) => { const key = `${r.student_id}:${r.exam_no}`; return <tr key={key} className="hover:bg-indigo-50/30"><td className="px-5 py-4"><input type="checkbox" aria-label={`选择${r.name}第${r.exam_no}次`} checked={selectedKeys.includes(key)} onChange={(e) => setSelectedKeys((old) => e.target.checked ? [...old, key] : old.filter((k) => k !== key))} /></td><td className="px-4 py-4"><Link href={`/students/${r.student_id}`} className="font-medium text-slate-800 hover:text-indigo-600">{r.name}</Link><p className="mt-1 text-[10px] text-slate-400">{r.student_no}</p></td><td className="px-4 py-4"><Link href={`/classes/${r.class_id}`} className="text-slate-600 hover:text-indigo-600">{r.class_no}</Link></td><td className="px-4 py-4 text-slate-500">第 {r.exam_no} 次</td><td className="px-4 py-4 font-semibold text-slate-800">{r.score}<span className="ml-1 text-[10px] font-normal text-slate-400">分</span></td><td className="px-4 py-4"><Badge tone={Number(r.score) >= 80 ? "green" : Number(r.score) >= 60 ? "amber" : "rose"}>{r.grade} {Number(r.score) >= 80 ? "≥ 80" : Number(r.score) >= 60 ? "≥ 60" : "< 60"}</Badge></td><td className="px-4 py-4"><div className="flex gap-2"><button onClick={() => quickEdit(r)} className="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-1.5 text-xs text-indigo-600"><PencilLine size={12} />改分</button><button disabled={busy} onClick={() => remove(r.student_id, r.exam_no, r.name)} className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-1.5 text-xs text-rose-500"><Trash2 size={12} />删除</button></div></td></tr>; })}{(!data || !data.items.length) && <EmptyState title={loading ? "正在读取成绩…" : "暂无匹配成绩"} columns={7} />}</tbody></table></div>
      <div className="px-5 pb-5">{data && <Pagination page={data.page} total={data.total} pageSize={data.page_size} onPage={(p) => load(filters, p)} />}</div>
    </section>
    <p className="mt-3 text-[10px] text-slate-400">Excel 导入：使用模板，学号 + 考试序次唯一；已有成绩不覆盖。单次最多 1,000 行 / 5 MB，错误行会整批回滚。</p>
    {editRow && <Modal title={`修改成绩 · ${editRow.name} 第 ${editRow.exam_no} 次`} onClose={() => setEditRow(null)} onSubmit={saveEdit} saving={busy} error={editError}>
      <div className="rounded-xl bg-indigo-50/60 p-4 text-xs leading-6 text-slate-600"><p>学生：{editRow.name}（{editRow.student_no}）</p><p>班级：{editRow.class_no} · 第 {editRow.exam_no} 次考核 · 当前分数：<span className="font-semibold text-indigo-600">{editRow.score}</span></p></div>
      <Field label="新分数（0–100，可填小数）"><input className={inputClass} type="number" min={0} max={100} step="0.01" required value={editValue} onChange={(e) => setEditValue(e.target.value)} /></Field>
      <p className="text-xs leading-5 text-slate-400">保存后立即更新大表，不跳转页面。修改对象是「该学生第 {editRow.exam_no} 次成绩」，按业务定位，不按成绩主键。</p>
    </Modal>}
    {newOpen && <Modal title="录入新成绩" onClose={() => setNewOpen(false)} onSubmit={create} saving={busy} error={modalError}><Field label="选择学生 *"><select className={inputClass} required value={newForm.student_id} onChange={(e) => setNewForm({ ...newForm, student_id: e.target.value })}><option value="">请选择学生</option>{students.map((s) => <option key={s.id} value={s.id}>{s.name}（{s.student_no}）</option>)}</select></Field><Field label="考核序次 *"><input className={inputClass} type="number" required min={1} step={1} value={newForm.exam_no} onChange={(e) => setNewForm({ ...newForm, exam_no: e.target.value })} /></Field><Field label="分数 *"><input className={inputClass} type="number" min={0} max={100} required step="0.01" value={newForm.score} onChange={(e) => setNewForm({ ...newForm, score: e.target.value })} /></Field><p className="text-xs text-slate-400">重复序次将被拒绝，请使用上方业务表单修改已有成绩。</p></Modal>}
  </div>;
}
