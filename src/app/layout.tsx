import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Shell } from "@/components/Shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "沃林学生管理系统",
  description: "沃林教育 · 学生、成绩、就业、班级与老师一体化管理",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen antialiased">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
