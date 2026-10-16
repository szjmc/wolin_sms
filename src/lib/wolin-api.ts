import { and, asc, count, desc, eq, gte, inArray, like, lte, sql } from "drizzle-orm";
import { db } from "@/db";
import {
  classTeacherRelations,
  classes,
  employmentRecords,
  pastExperiences,
  scores,
  students,
  teachers,
} from "@/db/schema";
import { annualized, birthDateCutoff, calculateAge, todayIso } from "@/lib/age";
import { asNumber, asString, json204, jsonErr, jsonOk, money, pageData, readJson, readPage } from "@/lib/http";
import { ensureReady } from "@/lib/bootstrap";
import { handleStudentSearch } from "@/lib/student-api";
import { handleScoreTable } from "@/lib/score-api";
import { handleClassManagement } from "@/lib/class-api";
import { handleEmploymentManagement } from "@/lib/employment-api";
import { guardWrite, handleAuth } from "@/lib/auth-api";

// 有"已接受"Offer 的学生算已就业，否则待就业
async function acceptedStudentIds(): Promise<Set<number>> {
  const rows = await db.selectDistinct({ studentId: employmentRecords.studentId }).from(employmentRecords)
    .innerJoin(students, eq(students.id, employmentRecords.studentId))
    .where(and(eq(employmentRecords.isDeleted, 0), eq(students.isDeleted, 0), eq(employmentRecords.offerStatus, "已接受")));
  return new Set(rows.map((r) => r.studentId));
}

function studentDto(row: typeof students.$inferSelect, classNo?: string | null, employed = false) {
  return {
    id: row.id,
    student_no: row.studentNo,
    class_id: row.classId,
    class_no: classNo ?? null,
    name: row.name,
    hometown: row.hometown,
    graduate_school: row.graduateSchool,
    major: row.major,
    training_enrollment_date: row.trainingEnrollmentDate,
    training_graduation_date: row.trainingGraduationDate,
    education: row.education,
    consultant_no: row.consultantNo,
    birth_date: row.birthDate,
    age: calculateAge(row.birthDate),
    gender: row.gender,
    employment_status: employed ? "已就业" : "待就业",
    avatar_url: row.avatarUrl,
    created_at: row.createdAt,
    updated_at: row.updatedAt,
  };
}

function classDto(row: typeof classes.$inferSelect) {
  return {
    id: row.id,
    class_no: row.classNo,
    class_name: row.className,
    start_date: row.startDate,
    completion_date: row.completionDate,
    class_status: row.classStatus,
    created_at: row.createdAt,
    updated_at: row.updatedAt,
  };
}

function teacherDto(row: typeof teachers.$inferSelect) {
  return {
    id: row.id,
    teacher_no: row.teacherNo,
    name: row.name,
    gender: row.gender,
    specialty: row.specialty,
    phone: row.phone,
    contact_info: row.contactInfo,
    teaching_years: money(row.teachingYears),
    teacher_status: row.teacherStatus,
    teaching_status: row.teachingStatus,
    created_at: row.createdAt,
    updated_at: row.updatedAt,
  };
}

function scoreDto(row: typeof scores.$inferSelect) {
  return {
    id: row.id,
    student_id: row.studentId,
    exam_no: row.examNo,
    score: money(row.score),
    created_at: row.createdAt,
    updated_at: row.updatedAt,
  };
}

function empDto(row: typeof employmentRecords.$inferSelect) {
  return {
    id: row.id,
    student_id: row.studentId,
    student_name_snapshot: row.studentNameSnapshot,
    class_no_snapshot: row.classNoSnapshot,
    employment_open_date: row.employmentOpenDate,
    offer_date: row.offerDate,
    company_name: row.companyName,
    employment_city: row.employmentCity,
    position: row.position,
    salary_amount: money(row.salaryAmount),
    salary_period: row.salaryPeriod,
    annualized_salary: annualized(row.salaryAmount, row.salaryPeriod),
    created_at: row.createdAt,
    updated_at: row.updatedAt,
  };
}

function expDto(row: typeof pastExperiences.$inferSelect) {
  return {
    id: row.id,
    student_id: row.studentId,
    past_salary_amount: row.pastSalaryAmount == null ? null : money(row.pastSalaryAmount),
    past_salary_period: row.pastSalaryPeriod,
    work_years: money(row.workYears),
    graduation_date: row.graduationDate,
    intended_city: row.intendedCity,
    previous_position: row.previousPosition,
    created_at: row.createdAt,
    updated_at: row.updatedAt,
  };
}

async function getClass(id: number) {
  const [row] = await db.select().from(classes).where(and(eq(classes.id, id), eq(classes.isDeleted, 0))).limit(1);
  return row ?? null;
}
async function getTeacher(id: number) {
  const [row] = await db.select().from(teachers).where(and(eq(teachers.id, id), eq(teachers.isDeleted, 0))).limit(1);
  return row ?? null;
}
async function getStudent(id: number) {
  const [row] = await db.select().from(students).where(and(eq(students.id, id), eq(students.isDeleted, 0))).limit(1);
  return row ?? null;
}

export async function handleWolin(method: string, slug: string[], request: Request): Promise<Response> {
  await ensureReady();
  const path = slug.join("/");
  const url = new URL(request.url);
  const { page, pageSize } = readPage(url);

  try {
    // 登录注册 / 用户管理接口先走认证模块
    const authResponse = await handleAuth(method, slug, request);
    if (authResponse) return authResponse;
    // 写操作统一过权限闸门：未登录 401，越权 403
    const denied = await guardWrite(method, path, request);
    if (denied) return denied;

    const studentSearch = await handleStudentSearch(method, slug, request);
    if (studentSearch) return studentSearch;
    const scoreTable = await handleScoreTable(method, slug, request);
    if (scoreTable) return scoreTable;
    const classManagement = await handleClassManagement(method, slug, request);
    if (classManagement) return classManagement;
    const employmentManagement = await handleEmploymentManagement(method, slug, request);
    if (employmentManagement) return employmentManagement;
    if (path === "health" && method === "GET") return jsonOk({ status: "ok" });

    // ---------- 班级 ----------
    if (path === "classes" && method === "GET") {
      const classNo = url.searchParams.get("class_no");
      const className = url.searchParams.get("class_name");
      const classStatus = url.searchParams.get("class_status");
      const filters = [eq(classes.isDeleted, 0)];
      if (classNo) filters.push(eq(classes.classNo, classNo));
      if (className) filters.push(like(classes.className, `%${className}%`));
      if (classStatus) filters.push(eq(classes.classStatus, classStatus));
      const where = and(...filters);
      const [{ total }] = await db.select({ total: count() }).from(classes).where(where);
      const rows = await db.select().from(classes).where(where).orderBy(asc(classes.id)).limit(pageSize).offset((page - 1) * pageSize);
      return jsonOk(pageData(rows.map(classDto), Number(total), page, pageSize));
    }
    if (path === "classes" && method === "POST") {
      const body = await readJson(request);
      if (!body) return jsonErr(422, "请求参数校验失败");
      const classNo = asString(body.class_no);
      const className = asString(body.class_name);
      const startDate = asString(body.start_date);
      if (!classNo || !className || !startDate) return jsonErr(422, "班级编号、名称、开班日期必填");
      const completionDate = body.completion_date == null ? null : asString(body.completion_date) ?? null;
      if (completionDate && completionDate < startDate) return jsonErr(422, "班级结课日期不能早于开班日期");
      const dup = await db.select({ id: classes.id }).from(classes).where(eq(classes.classNo, classNo)).limit(1);
      if (dup.length) return jsonErr(409, "班级编号已存在");
      const [row] = await db
        .insert(classes)
        .values({ classNo, className, startDate, completionDate, classStatus: asString(body.class_status) || "在读" })
        .returning();
      return jsonOk(classDto(row), 201);
    }
    if (slug[0] === "classes" && slug.length === 2 && /^\d+$/.test(slug[1])) {
      const id = Number(slug[1]);
      const row = await getClass(id);
      if (!row) return jsonErr(404, "班级不存在或已删除");
      if (method === "GET") return jsonOk(classDto(row));
      if (method === "PATCH") {
        const body = await readJson(request);
        if (!body) return jsonErr(422, "请求参数校验失败");
        const patch: Partial<typeof classes.$inferInsert> = { updatedAt: new Date() };
        if ("class_name" in body) {
          if (body.class_name == null) return jsonErr(422, "班级名称不能为空");
          patch.className = asString(body.class_name);
        }
        if ("start_date" in body) {
          if (body.start_date == null) return jsonErr(422, "开班日期不能为空");
          patch.startDate = asString(body.start_date);
        }
        if ("completion_date" in body) patch.completionDate = body.completion_date == null ? null : asString(body.completion_date);
        if ("class_status" in body) {
          if (body.class_status == null) return jsonErr(422, "班级状态不能为空");
          patch.classStatus = asString(body.class_status);
        }
        const startDate = patch.startDate ?? row.startDate;
        const completionDate = "completionDate" in patch ? patch.completionDate : row.completionDate;
        if (completionDate && startDate && completionDate < startDate) return jsonErr(400, "班级结课日期不能早于开班日期");
        const [updated] = await db.update(classes).set(patch).where(eq(classes.id, id)).returning();
        return jsonOk(classDto(updated));
      }
      if (method === "DELETE") {
        const [{ n }] = await db.select({ n: count() }).from(students).where(and(eq(students.classId, id), eq(students.isDeleted, 0)));
        if (Number(n) > 0) return jsonErr(409, "该班级下仍有学生，不能删除");
        const [{ r }] = await db.select({ r: count() }).from(classTeacherRelations).where(and(eq(classTeacherRelations.classId, id), eq(classTeacherRelations.isDeleted, 0)));
        if (Number(r) > 0) return jsonErr(409, "该班级还关联着老师，请先解除班级老师关系");
        await db.update(classes).set({ isDeleted: 1, deletedAt: new Date(), updatedAt: new Date() }).where(eq(classes.id, id));
        return json204();
      }
    }

    // ---------- 老师 ----------
    if (path === "teachers" && method === "GET") {
      const teacherNo = url.searchParams.get("teacher_no");
      const name = url.searchParams.get("name");
      const specialty = url.searchParams.get("specialty");
      const teacherStatus = url.searchParams.get("teacher_status");
      const filters = [eq(teachers.isDeleted, 0)];
      if (teacherNo) filters.push(eq(teachers.teacherNo, teacherNo));
      if (name) filters.push(like(teachers.name, `%${name}%`));
      if (specialty) filters.push(like(teachers.specialty, `%${specialty}%`));
      if (teacherStatus) filters.push(eq(teachers.teacherStatus, teacherStatus));
      const where = and(...filters);
      const [{ total }] = await db.select({ total: count() }).from(teachers).where(where);
      const rows = await db.select().from(teachers).where(where).orderBy(asc(teachers.id)).limit(pageSize).offset((page - 1) * pageSize);
      return jsonOk(pageData(rows.map(teacherDto), Number(total), page, pageSize));
    }
    if (path === "teachers" && method === "POST") {
      const body = await readJson(request);
      if (!body) return jsonErr(422, "请求参数校验失败");
      const teacherNo = asString(body.teacher_no);
      const name = asString(body.name);
      if (!teacherNo || !name) return jsonErr(422, "老师编号和姓名必填");
      const years = body.teaching_years == null ? 0 : Number(body.teaching_years);
      if (Number.isNaN(years) || years < 0) return jsonErr(422, "教学年限不得为负");
      const dup = await db.select({ id: teachers.id }).from(teachers).where(eq(teachers.teacherNo, teacherNo)).limit(1);
      if (dup.length) return jsonErr(409, "老师编号已存在");
      const [row] = await db
        .insert(teachers)
        .values({
          teacherNo,
          name,
          gender: asString(body.gender) ?? null,
          specialty: asString(body.specialty) ?? null,
          phone: asString(body.phone) ?? null,
          contactInfo: asString(body.contact_info) ?? null,
          teachingYears: years.toFixed(2),
          teacherStatus: asString(body.teacher_status) || "在职",
        })
        .returning();
      return jsonOk(teacherDto(row), 201);
    }
    if (slug[0] === "teachers" && slug.length === 2 && /^\d+$/.test(slug[1])) {
      const id = Number(slug[1]);
      const row = await getTeacher(id);
      if (!row) return jsonErr(404, "老师不存在或已删除");
      if (method === "GET") return jsonOk(teacherDto(row));
      if (method === "PATCH") {
        const body = await readJson(request);
        if (!body) return jsonErr(422, "请求参数校验失败");
        const patch: Partial<typeof teachers.$inferInsert> = { updatedAt: new Date() };
        if ("name" in body) {
          if (body.name == null) return jsonErr(422, "姓名不能为空");
          patch.name = asString(body.name);
        }
        if ("gender" in body) patch.gender = body.gender == null ? null : asString(body.gender);
        if ("specialty" in body) patch.specialty = body.specialty == null ? null : asString(body.specialty);
        if ("phone" in body) patch.phone = body.phone == null ? null : asString(body.phone);
        if ("contact_info" in body) patch.contactInfo = body.contact_info == null ? null : asString(body.contact_info);
        if ("teaching_years" in body) {
          if (body.teaching_years == null) return jsonErr(422, "教学年限不能为空");
          const years = Number(body.teaching_years);
          if (Number.isNaN(years) || years < 0) return jsonErr(422, "教学年限不得为负");
          patch.teachingYears = years.toFixed(2);
        }
        if ("teacher_status" in body) {
          if (body.teacher_status == null) return jsonErr(422, "状态不能为空");
          patch.teacherStatus = asString(body.teacher_status);
        }
        const [updated] = await db.update(teachers).set(patch).where(eq(teachers.id, id)).returning();
        return jsonOk(teacherDto(updated));
      }
      if (method === "DELETE") {
        const [{ r }] = await db.select({ r: count() }).from(classTeacherRelations).where(and(eq(classTeacherRelations.teacherId, id), eq(classTeacherRelations.isDeleted, 0)));
        if (Number(r) > 0) return jsonErr(409, "该老师还关联着班级，请先解除班级老师关系");
        await db.update(teachers).set({ isDeleted: 1, deletedAt: new Date(), updatedAt: new Date() }).where(eq(teachers.id, id));
        return json204();
      }
    }

    // ---------- 班级老师 ----------
    if (slug[0] === "classes" && slug[2] === "teachers" && slug.length === 3 && method === "GET") {
      const classId = Number(slug[1]);
      if (!(await getClass(classId))) return jsonErr(404, "班级不存在或已删除");
      const where = and(eq(classTeacherRelations.classId, classId), eq(classTeacherRelations.isDeleted, 0), eq(teachers.isDeleted, 0));
      const [{ total }] = await db.select({ total: count() }).from(classTeacherRelations).innerJoin(teachers, eq(teachers.id, classTeacherRelations.teacherId)).where(where);
      const rows = await db
        .select()
        .from(classTeacherRelations)
        .innerJoin(teachers, eq(teachers.id, classTeacherRelations.teacherId))
        .where(where)
        .orderBy(asc(classTeacherRelations.id))
        .limit(pageSize)
        .offset((page - 1) * pageSize);
      const items = rows.map((r) => ({
        relation_id: r.class_teacher_relations.id,
        class_id: r.class_teacher_relations.classId,
        relation_type: r.class_teacher_relations.relationType,
        relation_created_at: r.class_teacher_relations.createdAt,
        teacher: teacherDto(r.teachers),
      }));
      return jsonOk(pageData(items, Number(total), page, pageSize));
    }
    if (slug[0] === "classes" && slug[2] === "teachers" && slug.length === 4) {
      const classId = Number(slug[1]);
      const teacherId = Number(slug[3]);
      if (method === "PUT") {
        if (!(await getClass(classId))) return jsonErr(404, "班级不存在或已删除");
        if (!(await getTeacher(teacherId))) return jsonErr(404, "老师不存在或已删除");
        const body = (await readJson(request)) ?? {};
        const relationType = asString(body.relation_type) || "授课老师";
        if (relationType !== "班主任" && relationType !== "授课老师") return jsonErr(422, "关系类型只能是班主任或授课老师");
        const [exist] = await db
          .select()
          .from(classTeacherRelations)
          .where(and(eq(classTeacherRelations.classId, classId), eq(classTeacherRelations.teacherId, teacherId), eq(classTeacherRelations.relationType, relationType), eq(classTeacherRelations.isDeleted, 0)))
          .limit(1);
        if (exist) {
          return jsonOk({ id: exist.id, class_id: exist.classId, teacher_id: exist.teacherId, relation_type: exist.relationType, created_at: exist.createdAt });
        }
        const [row] = await db.insert(classTeacherRelations).values({ classId, teacherId, relationType }).returning();
        return jsonOk({ id: row.id, class_id: row.classId, teacher_id: row.teacherId, relation_type: row.relationType, created_at: row.createdAt });
      }
      if (method === "DELETE") {
        const relationType = url.searchParams.get("relation_type");
        const filters = [eq(classTeacherRelations.classId, classId), eq(classTeacherRelations.teacherId, teacherId), eq(classTeacherRelations.isDeleted, 0)];
        if (relationType) filters.push(eq(classTeacherRelations.relationType, relationType));
        const rows = await db.select().from(classTeacherRelations).where(and(...filters));
        if (!rows.length) return jsonErr(404, "班级老师关系不存在或已解除");
        await db.update(classTeacherRelations).set({ isDeleted: 1, deletedAt: new Date(), updatedAt: new Date() }).where(and(...filters));
        return json204();
      }
    }

    // ---------- 学生 ----------
    if (path === "students" && method === "GET") {
      const studentNo = url.searchParams.get("student_no");
      const name = url.searchParams.get("name");
      const classId = url.searchParams.get("class_id");
      const gender = url.searchParams.get("gender");
      const ageGt = url.searchParams.get("age_gt");
      const filters = [eq(students.isDeleted, 0)];
      if (studentNo) filters.push(eq(students.studentNo, studentNo));
      if (name) filters.push(like(students.name, `%${name}%`));
      if (classId) filters.push(eq(students.classId, Number(classId)));
      if (gender) filters.push(eq(students.gender, gender));
      if (ageGt) filters.push(lte(students.birthDate, birthDateCutoff(Number(ageGt))));
      const where = and(...filters);
      const [{ total }] = await db.select({ total: count() }).from(students).where(where);
      const rows = await db.select().from(students).where(where).orderBy(asc(students.id)).limit(pageSize).offset((page - 1) * pageSize);
      const classRows = await db.select().from(classes);
      const classMap = Object.fromEntries(classRows.map((c) => [c.id, c.classNo]));
      return jsonOk(pageData(rows.map((r) => studentDto(r, classMap[r.classId])), Number(total), page, pageSize));
    }
    if (path === "students" && method === "POST") {
      const body = await readJson(request);
      if (!body) return jsonErr(422, "请求参数校验失败");
      const studentNo = asString(body.student_no);
      const name = asString(body.name);
      const classId = asNumber(body.class_id);
      const birthDate = asString(body.birth_date);
      const gender = asString(body.gender);
      if (!studentNo || !name || !classId || !birthDate || !gender) return jsonErr(422, "学生编号、班级、姓名、出生日期、性别必填");
      if (!["男", "女", "其他"].includes(gender)) return jsonErr(422, "性别只能是男、女、其他");
      if (birthDate > todayIso()) return jsonErr(422, "出生日期不能晚于今天");
      const enroll = body.training_enrollment_date == null ? null : asString(body.training_enrollment_date) ?? null;
      const grad = body.training_graduation_date == null ? null : asString(body.training_graduation_date) ?? null;
      if (enroll && grad && grad < enroll) return jsonErr(422, "培训结课日期不能早于培训入学日期");
      if (!(await getClass(classId))) return jsonErr(404, "班级不存在或已删除");
      const dup = await db.select({ id: students.id }).from(students).where(eq(students.studentNo, studentNo)).limit(1);
      if (dup.length) return jsonErr(409, "学生编号已存在");
      const [row] = await db
        .insert(students)
        .values({
          studentNo,
          classId,
          name,
          hometown: asString(body.hometown) ?? null,
          graduateSchool: asString(body.graduate_school) ?? null,
          major: asString(body.major) ?? null,
          trainingEnrollmentDate: enroll,
          trainingGraduationDate: grad,
          education: asString(body.education) ?? null,
          consultantNo: asString(body.consultant_no) ?? null,
          birthDate,
          gender,
        })
        .returning();
      const cls = await getClass(row.classId);
      return jsonOk(studentDto(row, cls?.classNo, (await acceptedStudentIds()).has(row.id)), 201);
    }
    if (slug[0] === "students" && slug.length === 2 && /^\d+$/.test(slug[1])) {
      const id = Number(slug[1]);
      const row = await getStudent(id);
      if (!row) return jsonErr(404, "学生不存在或已删除");
      if (method === "GET") {
        const cls = await getClass(row.classId);
        return jsonOk(studentDto(row, cls?.classNo, (await acceptedStudentIds()).has(row.id)));
      }
      if (method === "PATCH") {
        const body = await readJson(request);
        if (!body) return jsonErr(422, "请求参数校验失败");
        const patch: Partial<typeof students.$inferInsert> = { updatedAt: new Date() };
        if ("class_id" in body) {
          const classId = asNumber(body.class_id);
          if (!classId) return jsonErr(422, "班级不能为空");
          if (!(await getClass(classId))) return jsonErr(404, "班级不存在或已删除");
          patch.classId = classId;
        }
        if ("name" in body) {
          if (body.name == null) return jsonErr(422, "姓名不能为空");
          patch.name = asString(body.name);
        }
        if ("hometown" in body) patch.hometown = body.hometown == null ? null : asString(body.hometown);
        if ("graduate_school" in body) patch.graduateSchool = body.graduate_school == null ? null : asString(body.graduate_school);
        if ("major" in body) patch.major = body.major == null ? null : asString(body.major);
        if ("training_enrollment_date" in body) patch.trainingEnrollmentDate = body.training_enrollment_date == null ? null : asString(body.training_enrollment_date);
        if ("training_graduation_date" in body) patch.trainingGraduationDate = body.training_graduation_date == null ? null : asString(body.training_graduation_date);
        if ("education" in body) patch.education = body.education == null ? null : asString(body.education);
        if ("consultant_no" in body) patch.consultantNo = body.consultant_no == null ? null : asString(body.consultant_no);
        if ("birth_date" in body) {
          if (body.birth_date == null) return jsonErr(422, "出生日期不能为空");
          const birthDate = asString(body.birth_date)!;
          if (birthDate > todayIso()) return jsonErr(422, "出生日期不能晚于今天");
          patch.birthDate = birthDate;
        }
        if ("gender" in body) {
          if (body.gender == null) return jsonErr(422, "性别不能为空");
          patch.gender = asString(body.gender);
        }
        const enroll = patch.trainingEnrollmentDate !== undefined ? patch.trainingEnrollmentDate : row.trainingEnrollmentDate;
        const grad = patch.trainingGraduationDate !== undefined ? patch.trainingGraduationDate : row.trainingGraduationDate;
        if (enroll && grad && grad < enroll) return jsonErr(400, "培训结课日期不能早于培训入学日期");
        const [updated] = await db.update(students).set(patch).where(eq(students.id, id)).returning();
        const cls = await getClass(updated.classId);
        return jsonOk(studentDto(updated, cls?.classNo, (await acceptedStudentIds()).has(updated.id)));
      }
      if (method === "DELETE") {
        await db.update(students).set({ isDeleted: 1, deletedAt: new Date(), updatedAt: new Date() }).where(eq(students.id, id));
        return json204();
      }
    }

    // ---------- 成绩：按学生 + 考核序次 ----------
    if (path === "scores" && method === "POST") {
      const body = await readJson(request);
      if (!body) return jsonErr(422, "请求参数校验失败");
      const studentId = asNumber(body.student_id);
      const examNo = asNumber(body.exam_no);
      const scoreVal = asNumber(body.score);
      if (!studentId || !examNo || scoreVal == null) return jsonErr(422, "学生、考核序次、成绩必填");
      if (examNo < 1) return jsonErr(422, "考核序次必须是正整数");
      if (scoreVal < 0 || scoreVal > 100) return jsonErr(422, "成绩范围 0~100");
      if (!(await getStudent(studentId))) return jsonErr(404, "学生不存在或已删除");
      const [exist] = await db.select().from(scores).where(and(eq(scores.studentId, studentId), eq(scores.examNo, examNo), eq(scores.isDeleted, 0))).limit(1);
      if (exist) return jsonErr(409, "该学生这一次考核的成绩已存在，请按学生和考核序次修改");
      const [row] = await db.insert(scores).values({ studentId, examNo, score: scoreVal.toFixed(2) }).returning();
      return jsonOk(scoreDto(row), 201);
    }
    if (slug[0] === "students" && slug[2] === "scores" && slug.length === 3 && method === "GET") {
      const studentId = Number(slug[1]);
      if (!(await getStudent(studentId))) return jsonErr(404, "学生不存在或已删除");
      const examNo = url.searchParams.get("exam_no");
      const filters = [eq(scores.studentId, studentId), eq(scores.isDeleted, 0)];
      if (examNo) filters.push(eq(scores.examNo, Number(examNo)));
      const where = and(...filters);
      const [{ total }] = await db.select({ total: count() }).from(scores).where(where);
      const rows = await db.select().from(scores).where(where).orderBy(asc(scores.examNo)).limit(pageSize).offset((page - 1) * pageSize);
      return jsonOk(pageData(rows.map(scoreDto), Number(total), page, pageSize));
    }
    if (slug[0] === "students" && slug[2] === "scores" && slug.length === 4) {
      const studentId = Number(slug[1]);
      const examNo = Number(slug[3]);
      if (!(await getStudent(studentId))) return jsonErr(404, "学生不存在或已删除");
      const [row] = await db.select().from(scores).where(and(eq(scores.studentId, studentId), eq(scores.examNo, examNo), eq(scores.isDeleted, 0))).limit(1);
      if (!row) return jsonErr(404, "该学生这一次考核的成绩不存在或已删除");
      if (method === "GET") return jsonOk(scoreDto(row));
      if (method === "PATCH") {
        const body = await readJson(request);
        if (!body || body.score == null) return jsonErr(422, "请提交新的分数");
        const scoreVal = asNumber(body.score);
        if (scoreVal == null || scoreVal < 0 || scoreVal > 100) return jsonErr(422, "成绩范围 0~100");
        const [updated] = await db.update(scores).set({ score: scoreVal.toFixed(2), updatedAt: new Date() }).where(eq(scores.id, row.id)).returning();
        return jsonOk(scoreDto(updated));
      }
      if (method === "DELETE") {
        await db.update(scores).set({ isDeleted: 1, deletedAt: new Date(), updatedAt: new Date() }).where(eq(scores.id, row.id));
        return json204();
      }
    }

    // ---------- 过往经历 ----------
    if (slug[0] === "students" && slug[2] === "past-experiences" && slug.length === 3) {
      const studentId = Number(slug[1]);
      if (!(await getStudent(studentId))) return jsonErr(404, "学生不存在或已删除");
      if (method === "GET") {
        const where = and(eq(pastExperiences.studentId, studentId), eq(pastExperiences.isDeleted, 0));
        const [{ total }] = await db.select({ total: count() }).from(pastExperiences).where(where);
        const rows = await db.select().from(pastExperiences).where(where).orderBy(asc(pastExperiences.id)).limit(pageSize).offset((page - 1) * pageSize);
        return jsonOk(pageData(rows.map(expDto), Number(total), page, pageSize));
      }
      if (method === "POST") {
        const body = (await readJson(request)) ?? {};
        const amount = body.past_salary_amount == null ? null : asNumber(body.past_salary_amount);
        const period = body.past_salary_period == null ? null : asString(body.past_salary_period);
        if (amount != null && amount < 0) return jsonErr(422, "过往薪资不能为负");
        if (amount != null && !period) return jsonErr(422, "填写过往薪资金额时必须同时填写薪资周期");
        const years = body.work_years == null ? 0 : Number(body.work_years);
        if (Number.isNaN(years) || years < 0) return jsonErr(422, "工作年限不得为负");
        const [row] = await db
          .insert(pastExperiences)
          .values({
            studentId,
            pastSalaryAmount: amount == null ? null : amount.toFixed(2),
            pastSalaryPeriod: period,
            workYears: years.toFixed(2),
            graduationDate: body.graduation_date == null ? null : asString(body.graduation_date),
            intendedCity: asString(body.intended_city) ?? null,
            previousPosition: asString(body.previous_position) ?? null,
          })
          .returning();
        return jsonOk(expDto(row), 201);
      }
    }
    if (slug[0] === "past-experiences" && slug.length === 2) {
      const id = Number(slug[1]);
      const [row] = await db.select().from(pastExperiences).where(and(eq(pastExperiences.id, id), eq(pastExperiences.isDeleted, 0))).limit(1);
      if (!row) return jsonErr(404, "过往经历不存在或已删除");
      if (!(await getStudent(row.studentId))) return jsonErr(404, "过往经历所属的学生不存在或已删除");
      if (method === "GET") return jsonOk(expDto(row));
      if (method === "PATCH") {
        const body = await readJson(request);
        if (!body) return jsonErr(422, "请求参数校验失败");
        const patch: Partial<typeof pastExperiences.$inferInsert> = { updatedAt: new Date() };
        if ("past_salary_amount" in body) patch.pastSalaryAmount = body.past_salary_amount == null ? null : Number(body.past_salary_amount).toFixed(2);
        if ("past_salary_period" in body) patch.pastSalaryPeriod = body.past_salary_period == null ? null : asString(body.past_salary_period);
        if ("work_years" in body) {
          if (body.work_years == null) return jsonErr(422, "工作年限不能为空");
          patch.workYears = Number(body.work_years).toFixed(2);
        }
        if ("graduation_date" in body) patch.graduationDate = body.graduation_date == null ? null : asString(body.graduation_date);
        if ("intended_city" in body) patch.intendedCity = body.intended_city == null ? null : asString(body.intended_city);
        if ("previous_position" in body) patch.previousPosition = body.previous_position == null ? null : asString(body.previous_position);
        const amount = patch.pastSalaryAmount !== undefined ? patch.pastSalaryAmount : row.pastSalaryAmount;
        const period = patch.pastSalaryPeriod !== undefined ? patch.pastSalaryPeriod : row.pastSalaryPeriod;
        if (amount != null && !period) return jsonErr(400, "填写过往薪资金额时必须同时填写薪资周期");
        const [updated] = await db.update(pastExperiences).set(patch).where(eq(pastExperiences.id, id)).returning();
        return jsonOk(expDto(updated));
      }
      if (method === "DELETE") {
        await db.update(pastExperiences).set({ isDeleted: 1, deletedAt: new Date(), updatedAt: new Date() }).where(eq(pastExperiences.id, id));
        return json204();
      }
    }

    // ---------- 就业 ----------
    if (path === "employment-records" && method === "POST") {
      const body = await readJson(request);
      if (!body) return jsonErr(422, "请求参数校验失败");
      const studentId = asNumber(body.student_id);
      const companyName = asString(body.company_name);
      const amount = asNumber(body.salary_amount);
      const period = asString(body.salary_period);
      if (!studentId || !companyName || amount == null || !period) return jsonErr(422, "学生、公司、薪资金额、薪资周期必填");
      if (amount < 0) return jsonErr(422, "薪资不能为负");
      if (period !== "MONTH" && period !== "YEAR") return jsonErr(422, "薪资周期只能是 MONTH 或 YEAR");
      const openDate = body.employment_open_date == null ? null : asString(body.employment_open_date) ?? null;
      const offerDate = body.offer_date == null ? null : asString(body.offer_date) ?? null;
      if (offerDate && !openDate) return jsonErr(422, "就业尚未开放，填写 Offer 日期之前请先填写就业开放日期");
      if (openDate && offerDate && offerDate < openDate) return jsonErr(422, "Offer 日期不能早于就业开放日期");
      const student = await getStudent(studentId);
      if (!student) return jsonErr(404, "学生不存在或已删除");
      const cls = await getClass(student.classId);
      if (!cls) return jsonErr(404, "学生所属班级不存在或已删除");
      const [row] = await db
        .insert(employmentRecords)
        .values({
          studentId,
          studentNameSnapshot: student.name,
          classNoSnapshot: cls.classNo,
          employmentOpenDate: openDate,
          offerDate,
          companyName,
          employmentCity: asString(body.employment_city) ?? null,
          position: asString(body.position) ?? null,
          salaryAmount: amount.toFixed(2),
          salaryPeriod: period,
        })
        .returning();
      return jsonOk(empDto(row), 201);
    }
    if (path === "employment-records" && method === "GET") {
      const studentNo = url.searchParams.get("student_no");
      const classId = url.searchParams.get("class_id");
      const companyName = url.searchParams.get("company_name");
      const city = url.searchParams.get("employment_city");
      const position = url.searchParams.get("position");
      const period = url.searchParams.get("salary_period");
      const minSalary = url.searchParams.get("min_salary");
      const maxSalary = url.searchParams.get("max_salary");
      const filters = [eq(employmentRecords.isDeleted, 0), eq(students.isDeleted, 0)];
      if (studentNo) filters.push(eq(students.studentNo, studentNo));
      if (classId) {
        const cls = await getClass(Number(classId));
        if (!cls) return jsonOk(pageData([], 0, page, pageSize));
        filters.push(eq(employmentRecords.classNoSnapshot, cls.classNo));
      }
      if (companyName) filters.push(like(employmentRecords.companyName, `%${companyName}%`));
      if (city) filters.push(like(employmentRecords.employmentCity, `%${city}%`));
      if (position) filters.push(like(employmentRecords.position, `%${position}%`));
      if (period) filters.push(eq(employmentRecords.salaryPeriod, period));
      if (minSalary) filters.push(gte(employmentRecords.salaryAmount, minSalary));
      if (maxSalary) filters.push(lte(employmentRecords.salaryAmount, maxSalary));
      const where = and(...filters);
      const [{ total }] = await db.select({ total: count() }).from(employmentRecords).innerJoin(students, eq(students.id, employmentRecords.studentId)).where(where);
      const rows = await db
        .select({ rec: employmentRecords })
        .from(employmentRecords)
        .innerJoin(students, eq(students.id, employmentRecords.studentId))
        .where(where)
        .orderBy(asc(employmentRecords.id))
        .limit(pageSize)
        .offset((page - 1) * pageSize);
      return jsonOk(pageData(rows.map((r) => empDto(r.rec)), Number(total), page, pageSize));
    }
    if (slug[0] === "students" && slug[2] === "employment-records" && slug.length === 3 && method === "GET") {
      const studentId = Number(slug[1]);
      if (!(await getStudent(studentId))) return jsonErr(404, "学生不存在或已删除");
      const where = and(eq(employmentRecords.studentId, studentId), eq(employmentRecords.isDeleted, 0));
      const [{ total }] = await db.select({ total: count() }).from(employmentRecords).where(where);
      const rows = await db.select().from(employmentRecords).where(where).orderBy(asc(employmentRecords.employmentOpenDate), asc(employmentRecords.id)).limit(pageSize).offset((page - 1) * pageSize);
      return jsonOk(pageData(rows.map(empDto), Number(total), page, pageSize));
    }
    if (slug[0] === "classes" && slug[2] === "employment-records" && slug.length === 3 && method === "GET") {
      const cls = await getClass(Number(slug[1]));
      if (!cls) return jsonErr(404, "班级不存在或已删除");
      const where = and(eq(employmentRecords.classNoSnapshot, cls.classNo), eq(employmentRecords.isDeleted, 0), eq(students.isDeleted, 0));
      const [{ total }] = await db.select({ total: count() }).from(employmentRecords).innerJoin(students, eq(students.id, employmentRecords.studentId)).where(where);
      const rows = await db
        .select({ rec: employmentRecords })
        .from(employmentRecords)
        .innerJoin(students, eq(students.id, employmentRecords.studentId))
        .where(where)
        .orderBy(asc(employmentRecords.id))
        .limit(pageSize)
        .offset((page - 1) * pageSize);
      return jsonOk(pageData(rows.map((r) => empDto(r.rec)), Number(total), page, pageSize));
    }
    if (slug[0] === "employment-records" && slug.length === 2 && /^\d+$/.test(slug[1])) {
      const id = Number(slug[1]);
      const [row] = await db.select().from(employmentRecords).where(and(eq(employmentRecords.id, id), eq(employmentRecords.isDeleted, 0))).limit(1);
      if (!row) return jsonErr(404, "就业记录不存在或已删除");
      if (!(await getStudent(row.studentId))) return jsonErr(404, "就业记录所属的学生不存在或已删除");
      if (method === "GET") return jsonOk(empDto(row));
      if (method === "PATCH") {
        const body = await readJson(request);
        if (!body) return jsonErr(422, "请求参数校验失败");
        const patch: Partial<typeof employmentRecords.$inferInsert> = { updatedAt: new Date() };
        if ("company_name" in body) {
          if (body.company_name == null) return jsonErr(422, "公司名称不能为空");
          patch.companyName = asString(body.company_name);
        }
        if ("employment_city" in body) patch.employmentCity = body.employment_city == null ? null : asString(body.employment_city);
        if ("position" in body) patch.position = body.position == null ? null : asString(body.position);
        if ("salary_amount" in body) {
          if (body.salary_amount == null) return jsonErr(422, "薪资不能为空");
          const amount = Number(body.salary_amount);
          if (amount < 0) return jsonErr(422, "薪资不能为负");
          patch.salaryAmount = amount.toFixed(2);
        }
        if ("salary_period" in body) {
          if (body.salary_period == null) return jsonErr(422, "薪资周期不能为空");
          patch.salaryPeriod = asString(body.salary_period);
        }
        if ("employment_open_date" in body) patch.employmentOpenDate = body.employment_open_date == null ? null : asString(body.employment_open_date);
        if ("offer_date" in body) patch.offerDate = body.offer_date == null ? null : asString(body.offer_date);
        const openDate = patch.employmentOpenDate !== undefined ? patch.employmentOpenDate : row.employmentOpenDate;
        const offerDate = patch.offerDate !== undefined ? patch.offerDate : row.offerDate;
        if (openDate && offerDate && offerDate < openDate) return jsonErr(400, "Offer 日期不能早于就业开放日期");
        const [updated] = await db.update(employmentRecords).set(patch).where(eq(employmentRecords.id, id)).returning();
        return jsonOk(empDto(updated));
      }
      if (method === "DELETE") {
        await db.update(employmentRecords).set({ isDeleted: 1, deletedAt: new Date(), updatedAt: new Date() }).where(eq(employmentRecords.id, id));
        return json204();
      }
    }

    // ---------- 统计 ----------
    if (path === "statistics/overview" && method === "GET") {
      const [{ studentTotal }] = await db.select({ studentTotal: count() }).from(students).where(eq(students.isDeleted, 0));
      const [{ classTotal }] = await db.select({ classTotal: count() }).from(classes).where(eq(classes.isDeleted, 0));
      const [{ teacherTotal }] = await db.select({ teacherTotal: count() }).from(teachers).where(eq(teachers.isDeleted, 0));
      const [{ empTotal }] = await db.select({ empTotal: count() }).from(employmentRecords).innerJoin(students, eq(students.id, employmentRecords.studentId)).where(and(eq(employmentRecords.isDeleted, 0), eq(students.isDeleted, 0)));
      return jsonOk({
        student_total: Number(studentTotal),
        class_total: Number(classTotal),
        teacher_total: Number(teacherTotal),
        employment_total: Number(empTotal),
      });
    }
    if (path === "statistics/students/over-age" && method === "GET") {
      const ageGt = Number(url.searchParams.get("age_gt") || 30);
      const cutoff = birthDateCutoff(ageGt);
      const where = and(eq(students.isDeleted, 0), lte(students.birthDate, cutoff));
      const [{ total }] = await db.select({ total: count() }).from(students).where(where);
      const rows = await db.select().from(students).where(where).orderBy(asc(students.birthDate)).limit(pageSize).offset((page - 1) * pageSize);
      const classRows = await db.select().from(classes);
      const classMap = Object.fromEntries(classRows.map((c) => [c.id, c.classNo]));
      return jsonOk(pageData(rows.map((r) => studentDto(r, classMap[r.classId])), Number(total), page, pageSize));
    }
    if (path === "statistics/classes/student-counts" && method === "GET") {
      const classId = url.searchParams.get("class_id");
      const classList = classId ? [await getClass(Number(classId))].filter(Boolean) : await db.select().from(classes).where(eq(classes.isDeleted, 0)).orderBy(asc(classes.id));
      if (classId && !classList.length) return jsonErr(404, "班级不存在或已删除");
      const grouped = await db
        .select({ classId: students.classId, gender: students.gender, n: count() })
        .from(students)
        .where(eq(students.isDeleted, 0))
        .groupBy(students.classId, students.gender);
      const map: Record<number, Record<string, number>> = {};
      for (const g of grouped) {
        if (!map[g.classId]) map[g.classId] = { 男: 0, 女: 0, 其他: 0 };
        map[g.classId][g.gender] = Number(g.n);
      }
      const result = (classList as NonNullable<(typeof classList)[0]>[]).map((c) => {
        const g = map[c.id] ?? { 男: 0, 女: 0, 其他: 0 };
        return {
          class_id: c.id,
          class_no: c.classNo,
          class_name: c.className,
          total_students: (g["男"] || 0) + (g["女"] || 0) + (g["其他"] || 0),
          male_count: g["男"] || 0,
          female_count: g["女"] || 0,
          other_count: g["其他"] || 0,
        };
      });
      return jsonOk(result);
    }
    if (path === "statistics/scores/all-at-least" && method === "GET") {
      const minScore = url.searchParams.get("min_score") || "80";
      const rows = await db
        .select({ studentId: scores.studentId })
        .from(scores)
        .innerJoin(students, eq(students.id, scores.studentId))
        .where(and(eq(scores.isDeleted, 0), eq(students.isDeleted, 0)))
        .groupBy(scores.studentId)
        .having(sql`min(${scores.score}) >= ${minScore}`);
      const ids = rows.map((r) => r.studentId);
      if (!ids.length) return jsonOk([]);
      const list = await db.select().from(students).where(and(eq(students.isDeleted, 0), inArray(students.id, ids))).orderBy(asc(students.id));
      const classRows = await db.select().from(classes);
      const classMap = Object.fromEntries(classRows.map((c) => [c.id, c.classNo]));
      return jsonOk(list.map((r) => studentDto(r, classMap[r.classId])));
    }
    if (path === "statistics/scores/failures" && method === "GET") {
      const failScore = url.searchParams.get("fail_score") || "60";
      const minFail = Number(url.searchParams.get("min_fail_count") || 3);
      const rows = await db
        .select({ studentId: scores.studentId, failCount: count() })
        .from(scores)
        .innerJoin(students, eq(students.id, scores.studentId))
        .where(and(eq(scores.isDeleted, 0), eq(students.isDeleted, 0), sql`${scores.score} < ${failScore}`))
        .groupBy(scores.studentId)
        .having(sql`count(${scores.id}) >= ${minFail}`)
        .orderBy(desc(count()));
      const classRows = await db.select().from(classes);
      const classMap = Object.fromEntries(classRows.map((c) => [c.id, c]));
      const result = [];
      for (const r of rows) {
        const s = await getStudent(r.studentId);
        if (!s) continue;
        const cls = classMap[s.classId];
        result.push({ student_id: s.id, student_no: s.studentNo, name: s.name, class_id: s.classId, class_no: cls?.classNo ?? "", class_name: cls?.className ?? "", fail_count: Number(r.failCount) });
      }
      return jsonOk(result);
    }
    if (path === "statistics/scores/class-averages" && method === "GET") {
      const examNo = url.searchParams.get("exam_no");
      const classId = url.searchParams.get("class_id");
      const filters = [eq(scores.isDeleted, 0), eq(students.isDeleted, 0), eq(classes.isDeleted, 0)];
      if (examNo) filters.push(eq(scores.examNo, Number(examNo)));
      if (classId) filters.push(eq(classes.id, Number(classId)));
      const rows = await db
        .select({
          classId: classes.id,
          classNo: classes.classNo,
          className: classes.className,
          examNo: scores.examNo,
          average: sql<string>`round(avg(${scores.score})::numeric, 2)`,
          sample: sql<number>`count(${scores.id})`,
        })
        .from(scores)
        .innerJoin(students, eq(students.id, scores.studentId))
        .innerJoin(classes, eq(classes.id, students.classId))
        .where(and(...filters))
        .groupBy(classes.id, classes.classNo, classes.className, scores.examNo)
        .orderBy(asc(scores.examNo), asc(classes.id));
      return jsonOk(rows.map((r) => ({ class_id: r.classId, class_no: r.classNo, class_name: r.className, exam_no: r.examNo, average_score: money(r.average), sample_count: Number(r.sample) })));
    }
    if (path === "statistics/employment/top-salaries" && method === "GET") {
      const limit = Math.min(100, Math.max(1, Number(url.searchParams.get("limit") || 5)));
      const rows = await db
        .select()
        .from(employmentRecords)
        .innerJoin(students, eq(students.id, employmentRecords.studentId))
        .where(and(eq(employmentRecords.isDeleted, 0), eq(students.isDeleted, 0)))
        .orderBy(sql`case when ${employmentRecords.salaryPeriod} = 'MONTH' then ${employmentRecords.salaryAmount} * 12 else ${employmentRecords.salaryAmount} end desc`, asc(employmentRecords.id))
        .limit(limit);
      return jsonOk(
        rows.map((r, i) => ({
          rank: i + 1,
          employment_record_id: r.employment_records.id,
          student_id: r.employment_records.studentId,
          student_name_snapshot: r.employment_records.studentNameSnapshot,
          class_no_snapshot: r.employment_records.classNoSnapshot,
          education: r.students.education,
          company_name: r.employment_records.companyName,
          employment_city: r.employment_records.employmentCity,
          position: r.employment_records.position,
          offer_date: r.employment_records.offerDate,
          salary_amount: money(r.employment_records.salaryAmount),
          salary_period: r.employment_records.salaryPeriod,
          annualized_salary: annualized(r.employment_records.salaryAmount, r.employment_records.salaryPeriod),
        })),
      );
    }
    if (path === "statistics/employment/durations" && method === "GET") {
      const studentId = url.searchParams.get("student_id");
      const classId = url.searchParams.get("class_id");
      const filters = [
        eq(employmentRecords.isDeleted, 0),
        eq(students.isDeleted, 0),
        sql`${employmentRecords.employmentOpenDate} is not null`,
        sql`${employmentRecords.offerDate} is not null`,
      ];
      if (studentId) {
        if (!(await getStudent(Number(studentId)))) return jsonErr(404, "学生不存在或已删除");
        filters.push(eq(employmentRecords.studentId, Number(studentId)));
      }
      if (classId) {
        const cls = await getClass(Number(classId));
        if (!cls) return jsonErr(404, "班级不存在或已删除");
        filters.push(eq(employmentRecords.classNoSnapshot, cls.classNo));
      }
      const rows = await db
        .select()
        .from(employmentRecords)
        .innerJoin(students, eq(students.id, employmentRecords.studentId))
        .where(and(...filters))
        .orderBy(asc(employmentRecords.id));
      return jsonOk(
        rows.map((r) => {
          const open = r.employment_records.employmentOpenDate!;
          const offer = r.employment_records.offerDate!;
          const duration = Math.round((new Date(offer).getTime() - new Date(open).getTime()) / 86400000);
          return {
            employment_record_id: r.employment_records.id,
            student_id: r.employment_records.studentId,
            student_name_snapshot: r.employment_records.studentNameSnapshot,
            class_no_snapshot: r.employment_records.classNoSnapshot,
            company_name: r.employment_records.companyName,
            employment_open_date: open,
            offer_date: offer,
            duration_days: duration,
          };
        }),
      );
    }
    if (path === "statistics/employment/class-average-durations" && method === "GET") {
      const classId = url.searchParams.get("class_id");
      const filters = [
        eq(employmentRecords.isDeleted, 0),
        eq(students.isDeleted, 0),
        sql`${employmentRecords.employmentOpenDate} is not null`,
        sql`${employmentRecords.offerDate} is not null`,
      ];
      if (classId) {
        const cls = await getClass(Number(classId));
        if (!cls) return jsonErr(404, "班级不存在或已删除");
        filters.push(eq(employmentRecords.classNoSnapshot, cls.classNo));
      }
      const rows = await db.select().from(employmentRecords).innerJoin(students, eq(students.id, employmentRecords.studentId)).where(and(...filters));
      const groups: Record<string, { total: number; count: number }> = {};
      for (const r of rows) {
        const key = r.employment_records.classNoSnapshot ?? "";
        const duration = Math.round((new Date(r.employment_records.offerDate!).getTime() - new Date(r.employment_records.employmentOpenDate!).getTime()) / 86400000);
        if (!groups[key]) groups[key] = { total: 0, count: 0 };
        groups[key].total += duration;
        groups[key].count += 1;
      }
      return jsonOk(
        Object.entries(groups).map(([class_no_snapshot, g]) => ({
          class_no_snapshot: class_no_snapshot || null,
          record_count: g.count,
          average_duration_days: (g.total / g.count).toFixed(2),
        })),
      );
    }

    return jsonErr(404, "接口不存在");
  } catch (error) {
    console.error(error);
    return jsonErr(500, "服务器内部错误，请联系管理员");
  }
}
