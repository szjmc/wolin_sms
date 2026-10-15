import { and, asc, count, eq, like, lte, or } from "drizzle-orm";
import { db } from "@/db";
import { classes, students } from "@/db/schema";
import { birthDateCutoff, calculateAge } from "@/lib/age";
import { jsonErr, jsonOk, pageData, readPage } from "@/lib/http";
import type { Student } from "@/lib/contracts";

export function studentView(row: typeof students.$inferSelect, classNo: string | null, className?: string | null): Student {
  // 学生一定有所属班级、出生日期必填，所以班级编号和年龄一定有值；?? 只是为了过类型检查。
  return {
    id: row.id, student_no: row.studentNo, name: row.name, class_id: row.classId,
    class_no: classNo ?? "", class_name: className ?? null, gender: row.gender,
    birth_date: row.birthDate, age: calculateAge(row.birthDate) ?? 0, hometown: row.hometown,
    graduate_school: row.graduateSchool, major: row.major, education: row.education,
    consultant_no: row.consultantNo, avatar_url: row.avatarUrl,
    training_enrollment_date: row.trainingEnrollmentDate, training_graduation_date: row.trainingGraduationDate,
    created_at: row.createdAt.toISOString(), updated_at: row.updatedAt.toISOString(),
  };
}

export async function handleStudentSearch(method: string, slug: string[], request: Request): Promise<Response | null> {
  if (method !== "GET" || slug.join("/") !== "students") return null;
  const url = new URL(request.url);
  const { page, pageSize } = readPage(url);
  const q = url.searchParams.get("q")?.trim();
  const name = url.searchParams.get("name");
  const studentNo = url.searchParams.get("student_no");
  const classId = url.searchParams.get("class_id");
  const gender = url.searchParams.get("gender");
  const ageGt = url.searchParams.get("age_gt");
  if (ageGt !== null && (!/^\d+$/.test(ageGt) || Number(ageGt) > 150)) return jsonErr(422, "年龄必须是 0–150 的整数");
  if (gender && !["男", "女", "其他"].includes(gender)) return jsonErr(422, "性别值不合法");
  if (classId && (!/^\d+$/.test(classId) || Number(classId) < 1)) return jsonErr(422, "班级 ID 不合法");
  const filters = [eq(students.isDeleted, 0)];
  // 输入一个关键词即可同时查姓名与学号；与其他筛选条件按 AND 组合。
  if (q) filters.push(or(like(students.name, `%${q}%`), like(students.studentNo, `%${q}%`))!);
  if (name) filters.push(like(students.name, `%${name}%`));
  if (studentNo) filters.push(eq(students.studentNo, studentNo));
  if (classId) filters.push(eq(students.classId, Number(classId)));
  if (gender) filters.push(eq(students.gender, gender));
  if (ageGt !== null) filters.push(lte(students.birthDate, birthDateCutoff(Number(ageGt))));
  const where = and(...filters);
  const [{ total }] = await db.select({ total: count() }).from(students).where(where);
  const rows = await db.select({ student: students, classNo: classes.classNo, className: classes.className })
    .from(students).leftJoin(classes, eq(classes.id, students.classId)).where(where)
    .orderBy(asc(students.id)).limit(pageSize).offset((page - 1) * pageSize);
  return jsonOk(pageData(rows.map((r) => studentView(r.student, r.classNo, r.className)), Number(total), page, pageSize));
}
