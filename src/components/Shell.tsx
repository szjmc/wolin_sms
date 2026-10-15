"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { ArrowUpRight, BookOpenCheck, BriefcaseBusiness, CalendarDays, ChartNoAxesCombined, ChevronRight, GraduationCap, LayoutDashboard, Menu, PanelLeftClose, School, ShieldCheck, Users, UserRound, X } from "lucide-react";

const NAV = [
  { href: "/", label: "工作台", icon: LayoutDashboard },
  { href: "/students", label: "学生档案", icon: Users },
  { href: "/scores", label: "考核成绩", icon: BookOpenCheck },
  { href: "/employment", label: "就业管理", icon: BriefcaseBusiness },
  { href: "/classes", label: "班级管理", icon: School },
  { href: "/teachers", label: "教师管理", icon: UserRound },
  { href: "/scheduling", label: "班级排班与教师关系", icon: CalendarDays },
  { href: "/statistics", label: "统计分析", icon: ChartNoAxesCombined },
];
export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname(); const [open, setOpen] = useState(false);
  const current = NAV.find((item) => item.href === "/" ? pathname === "/" : pathname.startsWith(item.href));
  return <div className="flex min-h-screen bg-[#f7f8fc]">
    {open && <div className="fixed inset-0 z-30 bg-slate-900/30 lg:hidden" onClick={() => setOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-[226px] flex-col border-r border-slate-200/80 bg-white transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
      <Link href="/" className="flex h-[76px] items-center gap-3 px-6"><span className="grid h-10 w-10 place-items-center rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-200"><GraduationCap size={23} /></span>
        <span><span className="block text-[17px] font-bold tracking-wider text-slate-900">沃林教育</span><span className="mt-0.5 block text-[9px] tracking-[.16em] text-slate-400">WOLIN EDUCATION</span></span></Link>
      <div className="mx-5 border-t border-slate-100" /><p className="px-6 pb-3 pt-7 text-[10px] font-medium tracking-wider text-slate-400">教务管理工作空间</p>
      <nav className="space-y-1.5 px-3">{NAV.map((item) => { const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href); const Icon = item.icon;
        return <Link key={item.href} href={item.href} onClick={() => setOpen(false)} className={`flex items-center gap-3 rounded-lg px-3.5 py-3 text-[13px] transition ${active ? "bg-indigo-50 font-semibold text-indigo-600" : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"}`}><Icon size={18} strokeWidth={active ? 2 : 1.7} />{item.label}{active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-indigo-500" />}</Link>;
      })}</nav>
      <div className="mt-auto p-5"><div className="rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-4"><div className="flex items-center gap-2 text-xs font-semibold text-indigo-600"><ShieldCheck size={15} />数据安全保护</div><p className="mt-2 text-[11px] leading-5 text-slate-400">业务数据采用逻辑删除<br />历史记录完整保留</p></div><p className="mt-5 text-center text-[10px] text-slate-300">沃林学生管理系统 · V1.4</p></div>
    </aside>
    <div className="min-w-0 flex-1 lg:ml-[226px]">
      <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-slate-200/70 bg-white/95 px-5 backdrop-blur lg:px-8">
        <div className="flex items-center gap-3"><button className="rounded-lg p-1.5 text-slate-500 lg:hidden" onClick={() => setOpen(!open)} aria-label="打开导航"><Menu size={20} /></button><div className="hidden items-center gap-2.5 text-xs text-slate-400 sm:flex"><span>教务中心</span><ChevronRight size={13} /><span className="font-medium text-slate-700">{current?.label ?? "详情"}</span>{pathname.split("/").length > 2 && <><ChevronRight size={13} /><span>详情</span></>}</div></div>
        <div className="flex items-center gap-5"><span className="hidden rounded-full border border-emerald-100 bg-emerald-50 px-2.5 py-1 text-[10px] text-emerald-600 sm:inline-flex">● 教务工作空间</span><div className="flex items-center gap-2.5 border-l border-slate-100 pl-5"><span className="grid h-8 w-8 place-items-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-600">教</span><span className="text-xs"><span className="block font-medium text-slate-700">教务管理员</span><span className="mt-0.5 block text-[10px] text-slate-400">沃林教育集团</span></span></div></div>
      </header>
      <main className="mx-auto max-w-[1600px] px-5 py-7 lg:px-8">{children}</main>
      <footer className="flex flex-wrap items-center justify-between gap-2 px-5 pb-6 pt-3 text-[10px] text-slate-400 lg:px-8"><span>© 沃林教育 · 让每一份成长都有迹可循</span><span>学生 · 教学 · 就业 一体化管理</span></footer>
    </div>
  </div>;
}
