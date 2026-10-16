"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { BookOpenCheck, BriefcaseBusiness, CalendarDays, ChartNoAxesCombined, ChevronDown, ChevronRight, GraduationCap, LayoutDashboard, LogOut, Menu, School, ShieldCheck, Users, UserCog, UserRound } from "lucide-react";
import { api, ApiError, clearSession, getToken } from "@/lib/client";
import { logout, ROLE_LABELS, type CurrentUser } from "@/lib/auth-client";

const NAV = [
  { href: "/dashboard", label: "工作台", icon: LayoutDashboard, roles: ["admin", "head_teacher", "teacher", "employment", "viewer"] },
  { href: "/students", label: "学生档案", icon: Users, roles: ["admin", "head_teacher", "teacher", "employment", "viewer"] },
  { href: "/scores", label: "考核成绩", icon: BookOpenCheck, roles: ["admin", "head_teacher", "teacher", "viewer"] },
  { href: "/employment", label: "就业管理", icon: BriefcaseBusiness, roles: ["admin", "head_teacher", "employment", "viewer"] },
  { href: "/classes", label: "班级管理", icon: School, roles: ["admin", "head_teacher", "teacher", "employment", "viewer"] },
  { href: "/teachers", label: "教师管理", icon: UserRound, roles: ["admin", "head_teacher", "viewer"] },
  { href: "/scheduling", label: "班级排班与教师关系", icon: CalendarDays, roles: ["admin", "head_teacher", "viewer"] },
  { href: "/statistics", label: "统计分析", icon: ChartNoAxesCombined, roles: ["admin", "head_teacher", "employment", "viewer"] },
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [accountMenu, setAccountMenu] = useState(false);
  const isAuthPage = pathname === "/" || pathname === "/login" || pathname === "/register";

  useEffect(() => {
    if (isAuthPage) { setAuthChecked(true); return; }
    let cancelled = false;
    async function verifySession() {
      if (!getToken()) { window.location.replace("/"); return; }
      try {
        const current = await api<CurrentUser>("/api/v1/auth/me");
        if (cancelled) return;
        setUser(current);
        window.localStorage.setItem("wolin_user", JSON.stringify(current));
        setAuthChecked(true);
        if (pathname === "/users" && !["admin", "head_teacher"].includes(current.role)) window.location.replace("/dashboard");
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          clearSession();
          window.location.replace("/");
        } else {
          // 网络/服务故障不能被当成登录失效，不要反复重定向。
          setSessionError("暂时无法验证登录状态，请检查服务后重试。");
        }
      }
    }
    setAuthChecked(false);
    setSessionError(null);
    void verifySession();
    function onExpired() { clearSession(); window.location.replace("/"); }
    window.addEventListener("wolin:session-expired", onExpired);
    return () => { cancelled = true; window.removeEventListener("wolin:session-expired", onExpired); };
  }, [pathname, isAuthPage, retry]);

  // 登录、注册使用独立全屏布局，不显示工作台信息和侧栏。
  if (isAuthPage) return <>{children}</>;
  if (!authChecked || !user) return <div className="grid min-h-screen place-items-center bg-slate-50 text-sm text-slate-500"><div className="text-center"><p>{sessionError ?? "正在验证登录状态…"}</p>{sessionError && <button className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-white" onClick={() => setRetry((value) => value + 1)}>重新验证</button>}</div></div>;

  const visibleNav = NAV.filter((item) => item.roles.includes(user.role));
  const current = visibleNav.find((item) => item.href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(item.href));
  const canManageUsers = user.role === "admin" || user.role === "head_teacher";

  async function signOut() {
    await logout();
    setUser(null);
    window.location.replace("/");
  }

  return <div className="flex min-h-screen bg-[#f7f8fc]">
    {open && <div className="fixed inset-0 z-30 bg-slate-900/30 lg:hidden" onClick={() => setOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-[226px] flex-col border-r border-slate-200/80 bg-white transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
      <Link href="/dashboard" className="flex h-[76px] items-center gap-3 px-6"><span className="grid h-10 w-10 place-items-center rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-200"><GraduationCap size={23} /></span>
        <span><span className="block text-[17px] font-bold tracking-wider text-slate-900">沃林教育</span><span className="mt-0.5 block text-[9px] tracking-[.16em] text-slate-400">WOLIN EDUCATION</span></span></Link>
      <div className="mx-5 border-t border-slate-100" /><p className="px-6 pb-3 pt-7 text-[10px] font-medium tracking-wider text-slate-400">教务管理工作空间</p>
      <nav className="space-y-1.5 px-3">{visibleNav.map((item) => { const active = item.href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(item.href); const Icon = item.icon;
        return <Link key={item.href} href={item.href} onClick={() => setOpen(false)} className={`flex items-center gap-3 rounded-lg px-3.5 py-3 text-[13px] transition ${active ? "bg-indigo-50 font-semibold text-indigo-600" : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"}`}><Icon size={18} strokeWidth={active ? 2 : 1.7} />{item.label}{active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-indigo-500" />}</Link>;
      })}</nav>
      <div className="mt-auto p-5"><div className="rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-4"><div className="flex items-center gap-2 text-xs font-semibold text-indigo-600"><ShieldCheck size={15} />账号权限已启用</div><p className="mt-2 text-[11px] leading-5 text-slate-400">当前角色：{ROLE_LABELS[user.role] ?? user.role}<br />业务数据按账号权限保护</p></div><p className="mt-5 text-center text-[10px] text-slate-300">沃林学生管理系统 · V1.5</p></div>
    </aside>
    <div className="min-w-0 flex-1 lg:ml-[226px]">
      <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-slate-200/70 bg-white/95 px-5 backdrop-blur lg:px-8">
        <div className="flex items-center gap-3"><button className="rounded-lg p-1.5 text-slate-500 lg:hidden" onClick={() => setOpen(!open)} aria-label="打开导航"><Menu size={20} /></button><div className="hidden items-center gap-2.5 text-xs text-slate-400 sm:flex"><span>教务中心</span><ChevronRight size={13} /><span className="font-medium text-slate-700">{current?.label ?? "用户信息"}</span>{pathname.split("/").length > 2 && <><ChevronRight size={13} /><span>详情</span></>}</div></div>
        <div className="relative flex items-center gap-5"><span className="hidden rounded-full border border-emerald-100 bg-emerald-50 px-2.5 py-1 text-[10px] text-emerald-600 sm:inline-flex">● 已登录</span>
          <button type="button" onClick={() => setAccountMenu(!accountMenu)} aria-expanded={accountMenu} className="flex items-center gap-2.5 rounded-xl border-l border-slate-100 pl-5 text-left hover:bg-slate-50">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-600">{user.display_name.slice(0, 1)}</span>
            <span className="text-xs"><span className="block font-medium text-slate-700">{user.display_name}</span><span className="mt-0.5 block text-[10px] text-slate-400">{ROLE_LABELS[user.role] ?? user.role}</span></span><ChevronDown size={14} className="text-slate-400" />
          </button>
          {accountMenu && <><button aria-label="关闭菜单" className="fixed inset-0 z-20 cursor-default" onClick={() => setAccountMenu(false)} /><div className="absolute right-0 top-12 z-30 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
            <div className="border-b border-slate-100 px-3 py-2"><p className="text-xs font-semibold text-slate-700">{user.display_name}</p><p className="mt-1 text-[10px] text-slate-400">{user.username} · {ROLE_LABELS[user.role]}</p></div>
            <Link onClick={() => setAccountMenu(false)} href="/profile" className="mt-1 flex items-center gap-2 rounded-lg px-3 py-2.5 text-xs text-slate-600 hover:bg-slate-50"><UserRound size={15} />个人信息</Link>
            {canManageUsers && <Link onClick={() => setAccountMenu(false)} href="/users" className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-xs text-slate-600 hover:bg-slate-50"><UserCog size={15} />用户管理</Link>}
            <button onClick={signOut} className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-xs text-rose-500 hover:bg-rose-50"><LogOut size={15} />退出登录</button>
          </div></>}
        </div>
      </header>
      <main className="mx-auto max-w-[1600px] px-5 py-7 lg:px-8">{children}</main>
      <footer className="flex flex-wrap items-center justify-between gap-2 px-5 pb-6 pt-3 text-[10px] text-slate-400 lg:px-8"><span>© 沃林教育 · 让每一份成长都有迹可循</span><span>学生 · 教学 · 就业 一体化管理</span></footer>
    </div>
  </div>;
}
