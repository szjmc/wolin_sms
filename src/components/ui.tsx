"use client";

import { useEffect, useRef, type ButtonHTMLAttributes, type FormEvent, type ReactNode } from "react";
import { AlertCircle, CheckCircle2, ChevronLeft, ChevronRight, Loader2, X } from "lucide-react";

export function PageHeader({ title, desc, action, eyebrow }: { title: string; desc?: string; action?: ReactNode; eyebrow?: string }) {
  return <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
    <div>{eyebrow && <p className="mb-2 text-[11px] font-semibold uppercase tracking-[.18em] text-indigo-500">{eyebrow}</p>}
      <h1 className="text-[26px] font-bold tracking-tight text-slate-900">{title}</h1>
      {desc && <p className="mt-2 text-[13px] leading-6 text-slate-500">{desc}</p>}
    </div>{action}</div>;
}

export function Button({ children, tone = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "primary" | "ghost" | "danger" | "success" }) {
  const styles = { primary: "bg-indigo-600 text-white shadow-sm shadow-indigo-200 hover:bg-indigo-700",
    ghost: "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
    danger: "bg-rose-50 text-rose-600 hover:bg-rose-100", success: "bg-emerald-600 text-white hover:bg-emerald-700" };
  return <button type="button" {...props} className={`inline-flex shrink-0 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-[13px] font-medium transition disabled:cursor-not-allowed disabled:opacity-45 ${styles[tone]} ${className}`}>{children}</button>;
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "green" | "amber" | "rose" | "indigo" }) {
  const map = { slate: "bg-slate-100 text-slate-500", green: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-700", rose: "bg-rose-50 text-rose-600", indigo: "bg-indigo-50 text-indigo-600" };
  return <span className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium ${map[tone]}`}>{children}</span>;
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return <label className="block min-w-0"><span className="mb-2 block text-xs font-medium text-slate-500">{label}</span>{children}{hint && <span className="mt-1.5 block text-[11px] text-slate-400">{hint}</span>}</label>;
}
export const inputClass = "h-11 w-full min-w-0 rounded-lg border border-slate-200 bg-white px-3 text-[13px] text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-3 focus:ring-indigo-100 disabled:bg-slate-50";

export function Dialog({ title, description, children, onClose, wide = false }: { title: string; description?: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    ref.current?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const items = ref.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),a[href],textarea');
        if (!items?.length) return;
        const first = items[0]; const last = items[items.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("keydown", key); document.body.style.overflow = originalOverflow; previous?.focus(); };
  }, [onClose]);
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/35 p-4 backdrop-blur-sm" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
    <div role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref} className={`max-h-[90vh] w-full overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl outline-none ${wide ? "max-w-3xl" : "max-w-xl"}`}>
      <div className="mb-5 flex items-start justify-between gap-3"><div><h2 className="text-lg font-semibold text-slate-900">{title}</h2>{description && <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>}</div>
        <button type="button" aria-label="关闭弹窗" onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"><X size={19} /></button></div>
      {children}
    </div></div>;
}

export function Modal({ title, children, onClose, onSubmit, saving, error, wide }: { title: string; children: ReactNode; onClose: () => void; onSubmit: (event: FormEvent) => void; saving?: boolean; error?: string | null; wide?: boolean }) {
  return <Dialog title={title} onClose={onClose} wide={wide}><form onSubmit={onSubmit}><ErrorText error={error ?? null} /><div className="grid gap-4">{children}</div>
    <div className="mt-6 flex justify-end gap-2 border-t border-slate-100 pt-5"><Button tone="ghost" onClick={onClose}>取消</Button><Button type="submit" disabled={saving}>{saving && <Loader2 size={15} className="animate-spin" />}{saving ? "保存中…" : "保存"}</Button></div></form></Dialog>;
}

export function Table({ headers, children }: { headers: string[]; children: ReactNode }) {
  return <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white"><table className="w-full whitespace-nowrap text-left text-[13px]">
    <thead className="bg-slate-50/80 text-[11px] text-slate-500"><tr>{headers.map((h) => <th key={h} className="px-5 py-3.5 font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{children}</tbody></table></div>;
}

export function Pagination({ page, total, pageSize, onPage }: { page: number; total: number; pageSize: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400"><span>共 {total} 条记录 · 每页 {pageSize} 条</span>
    <div className="flex items-center gap-3"><Button tone="ghost" aria-label="上一页" disabled={page <= 1} onClick={() => onPage(page - 1)} className="!p-2"><ChevronLeft size={16} /></Button>
      <span className="text-slate-500">{page} / {pages}</span><Button tone="ghost" aria-label="下一页" disabled={page >= pages} onClick={() => onPage(page + 1)} className="!p-2"><ChevronRight size={16} /></Button></div></div>;
}
export function ErrorText({ error }: { error: string | null }) {
  return error ? <div role="alert" className="mb-4 flex items-start gap-2 rounded-lg border border-rose-100 bg-rose-50 p-3 text-xs leading-5 text-rose-600"><AlertCircle size={16} className="mt-0.5 shrink-0" />{error}</div> : null;
}
export function SuccessText({ message }: { message: string | null }) {
  return message ? <div role="status" className="mb-4 flex items-start gap-2 rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-xs leading-5 text-emerald-600"><CheckCircle2 size={16} className="mt-0.5 shrink-0" />{message}</div> : null;
}
export function EmptyState({ title = "暂无数据", description = "试试调整筛选条件，或添加一条新记录。", columns }: { title?: string; description?: string; columns?: number }) {
  const inner = <div className="py-14 text-center"><div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-slate-50 text-slate-300"><AlertCircle size={22} /></div><p className="text-sm font-medium text-slate-500">{title}</p><p className="mt-2 text-xs text-slate-400">{description}</p></div>;
  return columns ? <tr><td colSpan={columns}>{inner}</td></tr> : inner;
}
export function StatCard({ label, value, icon, description }: { label: string; value: ReactNode; icon: ReactNode; description?: string }) {
  return <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-5"><div><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-[25px] font-semibold tracking-tight text-slate-900">{value}</p>{description && <p className="mt-1 text-[11px] text-slate-400">{description}</p>}</div><div className="grid h-11 w-11 place-items-center rounded-xl bg-indigo-50 text-indigo-500">{icon}</div></div>;
}
