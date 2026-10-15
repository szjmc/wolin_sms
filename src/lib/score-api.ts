import ExcelJS from "exceljs";
import { and, asc, count, desc, eq, gte, like, lte, or, sql } from "drizzle-orm";
import { db } from "@/db";
import { classes, scores, students } from "@/db/schema";
import { jsonErr, jsonOk, pageData, readPage } from "@/lib/http";
import type { Score } from "@/lib/contracts";

const MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function scoreFilters(url: URL) {
  const filters = [eq(scores.isDeleted, 0), eq(students.isDeleted, 0), eq(classes.isDeleted, 0)];
  const q = url.searchParams.get("q")?.trim();
  const classId = url.searchParams.get("class_id");
  const studentId = url.searchParams.get("student_id");
  const examNo = url.searchParams.get("exam_no");
  const lower = url.searchParams.get("min_score");
  const upper = url.searchParams.get("max_score");
  const band = url.searchParams.get("score_band");
  if (q) filters.push(or(like(students.name, `%${q}%`), like(students.studentNo, `%${q}%`))!);
  if (classId) filters.push(eq(students.classId, Number(classId)));
  if (studentId) filters.push(eq(students.id, Number(studentId)));
  if (examNo) filters.push(eq(scores.examNo, Number(examNo)));
  if (lower !== null) filters.push(gte(scores.score, lower));
  if (upper !== null) filters.push(lte(scores.score, upper));
  if (band === "excellent") filters.push(gte(scores.score, "80"));
  if (band === "pass") filters.push(gte(scores.score, "60"), sql`${scores.score} < 80`);
  if (band === "fail") filters.push(sql`${scores.score} < 60`);
  const keys = url.searchParams.get("keys");
  if (keys) {
    const conditions = [];
    for (const key of keys.split(",")) {
      const [student, exam] = key.split(":").map(Number);
      if (student > 0 && exam > 0) conditions.push(and(eq(scores.studentId, student), eq(scores.examNo, exam))!);
    }
    if (conditions.length) filters.push(or(...conditions)!);
    else filters.push(sql`false`);
  }
  return and(...filters);
}

function validateFilters(url: URL) {
  for (const key of ["class_id", "student_id", "exam_no"]) {
    const value = url.searchParams.get(key);
    if (value && (!/^\d+$/.test(value) || Number(value) < 1)) return `${key} 必须是正整数`;
  }
  for (const key of ["min_score", "max_score"]) {
    const value = url.searchParams.get(key);
    if (value !== null && (!Number.isFinite(Number(value)) || Number(value) < 0 || Number(value) > 100)) return "分数范围是 0–100";
  }
  const min = url.searchParams.get("min_score");
  const max = url.searchParams.get("max_score");
  if (min !== null && max !== null && Number(min) > Number(max)) return "最低分不能大于最高分";
  if (url.searchParams.get("score_band") && !["excellent", "pass", "fail"].includes(url.searchParams.get("score_band")!)) return "分数段不合法";
  return null;
}

async function scoreRows(url: URL, paginate: boolean): Promise<Score[]> {
  const { page, pageSize } = readPage(url);
  const where = scoreFilters(url);
  const order = url.searchParams.get("sort");
  const sort = order === "score_desc" ? desc(scores.score) : order === "score_asc" ? asc(scores.score) : order === "exam_asc" ? asc(scores.examNo) : desc(scores.updatedAt);
  const query = db.select({ score: scores, name: students.name, studentNo: students.studentNo,
    classId: classes.id, classNo: classes.classNo, className: classes.className })
    .from(scores).innerJoin(students, eq(students.id, scores.studentId))
    .innerJoin(classes, eq(classes.id, students.classId)).where(where).orderBy(sort, desc(scores.id));
  const rows = paginate ? await query.limit(pageSize).offset((page - 1) * pageSize) : await query.limit(50001);
  return rows.map((r) => ({
    id: r.score.id, student_id: r.score.studentId, student_no: r.studentNo, name: r.name,
    class_id: r.classId, class_no: r.classNo, class_name: r.className, exam_no: r.score.examNo,
    score: Number(r.score.score).toFixed(2), grade: Number(r.score.score) >= 80 ? "优秀" : Number(r.score.score) >= 60 ? "及格" : "不及格",
    created_at: r.score.createdAt.toISOString(), updated_at: r.score.updatedAt.toISOString(),
  }));
}

async function exportScores(url: URL, template: boolean) {
  const rows = template ? [] : await scoreRows(url, false);
  if (rows.length > 50000) return jsonErr(422, "一次最多导出 50,000 条，请缩小筛选范围");
  const book = new ExcelJS.Workbook();
  const sheet = book.addWorksheet(template ? "成绩导入模板" : "考试成绩");
  sheet.columns = [
    { header: "学号", key: "student_no", width: 24 }, { header: "姓名", key: "name", width: 18 },
    { header: "班级", key: "class_no", width: 22 }, { header: "考试序次", key: "exam_no", width: 14 },
    { header: "分数", key: "score", width: 14 },
  ];
  for (const row of rows) sheet.addRow({ ...row, score: Number(row.score) });
  sheet.getRow(1).font = { bold: true, color: { argb: "FFFFFFFF" } };
  sheet.getRow(1).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF635BFF" } };
  sheet.views = [{ state: "frozen", ySplit: 1 }];
  sheet.autoFilter = "A1:E1";
  const buffer = await book.xlsx.writeBuffer();
  return new Response(new Uint8Array(buffer as ArrayBuffer), {
    headers: { "Content-Type": MIME, "Content-Disposition": `attachment; filename="${template ? "score-template" : "scores"}.xlsx"`, "Cache-Control": "no-store" },
  });
}

async function importScores(request: Request) {
  let form: FormData;
  try { form = await request.formData(); } catch { return jsonErr(422, "请上传 Excel 文件"); }
  const file = form.get("file");
  if (!(file instanceof File) || !file.name.toLowerCase().endsWith(".xlsx")) return jsonErr(422, "仅支持 .xlsx 文件，请先下载模板");
  if (file.size > 5 * 1024 * 1024) return jsonErr(413, "文件不能超过 5 MB");
  const book = new ExcelJS.Workbook();
  try { await book.xlsx.load(await file.arrayBuffer()); } catch { return jsonErr(422, "文件不是有效的 Excel 工作簿"); }
  const sheet = book.worksheets[0];
  if (!sheet || sheet.rowCount < 2) return jsonErr(422, "Excel 没有可导入的数据");
  if (sheet.rowCount > 1001) return jsonErr(422, "一次最多导入 1,000 行");
  const headers = sheet.getRow(1).values as ExcelJS.CellValue[];
  function column(choices: string[]) { return headers.findIndex((v) => choices.includes(String(v ?? "").trim())); }
  const noCol = column(["学号", "学生编号", "student_no"]);
  const examCol = column(["考试序次", "考核序次", "exam_no"]);
  const scoreCol = column(["分数", "成绩", "score"]);
  if (noCol < 1 || examCol < 1 || scoreCol < 1) return jsonErr(422, "缺少学号、考试序次或分数列");
  const errors: { field: string; reason: string }[] = [];
  const pending: { studentId: number; examNo: number; score: string }[] = [];
  const seen = new Set<string>();
  // 校验完所有行再统一写入；重复行或已有成绩绝不静默覆盖。
  for (let i = 2; i <= sheet.rowCount; i++) {
    const row = sheet.getRow(i);
    if (!row.hasValues) continue;
    const no = row.getCell(noCol).text.trim();
    const examValue = row.getCell(examCol).value;
    const scoreValue = row.getCell(scoreCol).value;
    if (typeof examValue === "object" || typeof scoreValue === "object" || scoreValue === null || scoreValue === "") {
      errors.push({ field: `第 ${i} 行`, reason: "序次和分数必须是实际数值，不能使用公式或空值" }); continue;
    }
    const exam = Number(examValue);
    const value = Number(scoreValue);
    if (!Number.isInteger(exam) || exam < 1 || exam > 2147483647 || !Number.isFinite(value) || value < 0 || value > 100 || Math.abs(value * 100 - Math.round(value * 100)) > 0.00001) {
      errors.push({ field: `第 ${i} 行`, reason: "序次必须是正整数；分数为 0–100，最多两位小数" }); continue;
    }
    const [student] = await db.select().from(students).where(and(eq(students.studentNo, no), eq(students.isDeleted, 0))).limit(1);
    if (!student) { errors.push({ field: `第 ${i} 行`, reason: `学生 ${no} 不存在或已删除` }); continue; }
    const key = `${student.id}:${exam}`;
    if (seen.has(key)) { errors.push({ field: `第 ${i} 行`, reason: "Excel 内同一学生的同一次考试重复" }); continue; }
    seen.add(key);
    const [existing] = await db.select({ id: scores.id }).from(scores).where(and(eq(scores.studentId, student.id), eq(scores.examNo, exam), eq(scores.isDeleted, 0))).limit(1);
    if (existing) { errors.push({ field: `第 ${i} 行`, reason: "该次成绩已存在，请使用保存修改功能" }); continue; }
    pending.push({ studentId: student.id, examNo: exam, score: value.toFixed(2) });
  }
  if (errors.length) return jsonErr(422, "导入未执行，请修正以下行后重试", errors);
  if (!pending.length) return jsonErr(422, "没有有效数据行");
  await db.transaction(async (tx) => {
    // 锁学生行并复查，避免检查后被另一请求插入同次成绩。
    for (const id of [...new Set(pending.map((r) => r.studentId))].sort((a, b) => a - b)) {
      await tx.execute(sql`select id from students where id = ${id} and is_deleted = 0 for update`);
    }
    for (const row of pending) {
      const [existing] = await tx.select().from(scores).where(and(eq(scores.studentId, row.studentId), eq(scores.examNo, row.examNo), eq(scores.isDeleted, 0))).limit(1);
      if (existing) throw new Error("IMPORT_CONFLICT");
    }
    await tx.insert(scores).values(pending);
  });
  return jsonOk({ imported: pending.length, message: `成功导入 ${pending.length} 条成绩` }, 201);
}

export async function handleScoreTable(method: string, slug: string[], request: Request): Promise<Response | null> {
  const path = slug.join("/");
  if (path === "scores/exams" && method === "GET") {
    const rows = await db.selectDistinct({ exam_no: scores.examNo }).from(scores).innerJoin(students, eq(students.id, scores.studentId))
      .where(and(eq(scores.isDeleted, 0), eq(students.isDeleted, 0))).orderBy(asc(scores.examNo));
    return jsonOk(rows.map((r) => r.exam_no));
  }
  if (!["scores", "scores/summary", "scores/export", "scores/template", "scores/import"].includes(path)) return null;
  if (path === "scores" && method !== "GET") return null;
  if (path === "scores/import" && method === "POST") {
    try { return await importScores(request); } catch (error) {
      if (error instanceof Error && error.message === "IMPORT_CONFLICT") return jsonErr(409, "导入期间成绩发生变化，整批已回滚，请刷新后重试");
      throw error;
    }
  }
  if (method !== "GET") return jsonErr(405, "请求方法不支持");
  const url = new URL(request.url);
  const invalid = validateFilters(url);
  if (invalid) return jsonErr(422, invalid);
  if (path === "scores/export") return exportScores(url, false);
  if (path === "scores/template") return exportScores(url, true);
  const where = scoreFilters(url);
  const [summary] = await db.select({ total: count(), average: sql<string | null>`round(avg(${scores.score}), 2)`,
    passCount: sql<number>`count(*) filter (where ${scores.score} >= 60)`,
    excellent: sql<number>`count(*) filter (where ${scores.score} >= 80)` })
    .from(scores).innerJoin(students, eq(students.id, scores.studentId)).innerJoin(classes, eq(classes.id, students.classId)).where(where);
  if (path === "scores/summary") return jsonOk({ total: Number(summary.total), average_score: summary.average,
    pass_count: Number(summary.passCount), excellent_count: Number(summary.excellent) });
  const { page, pageSize } = readPage(url);
  return jsonOk(pageData(await scoreRows(url, true), Number(summary.total), page, pageSize));
}
