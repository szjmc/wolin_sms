import { and, asc, count, eq, like, ne, sql } from "drizzle-orm";
import { db } from "@/db";
import { classTeacherRelations as relations, classes, employmentRecords, scores, students, teachers } from "@/db/schema";
import { asNumber, asString, json204, jsonErr, jsonOk, pageData, readJson, readPage } from "@/lib/http";
import type { ClassItem, Relation, Teacher } from "@/lib/contracts";

class AssignmentError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
type Transaction = Parameters<Parameters<typeof db.transaction>[0]>[0];

export function teacherView(row: typeof teachers.$inferSelect): Teacher {
  return {
    id: row.id, teacher_no: row.teacherNo, name: row.name, gender: row.gender,
    specialty: row.specialty, phone: row.phone, contact_info: row.contactInfo,
    teaching_years: Number(row.teachingYears).toFixed(2), teacher_status: row.teacherStatus,
    teaching_status: row.teachingStatus,
  };
}

export async function relationRows(classId?: number, teacherId?: number): Promise<Relation[]> {
  const filters = [eq(relations.isDeleted, 0), eq(classes.isDeleted, 0), eq(teachers.isDeleted, 0)];
  if (classId !== undefined) filters.push(eq(relations.classId, classId));
  if (teacherId !== undefined) filters.push(eq(relations.teacherId, teacherId));
  const rows = await db.select({ relation: relations, cls: classes, teacher: teachers }).from(relations)
    .innerJoin(classes, eq(classes.id, relations.classId)).innerJoin(teachers, eq(teachers.id, relations.teacherId))
    .where(and(...filters)).orderBy(asc(classes.id), asc(relations.id));
  return rows.map((r) => ({ id: r.relation.id, class_id: r.cls.id, class_no: r.cls.classNo,
    class_name: r.cls.className, class_status: r.cls.classStatus, teacher_id: r.teacher.id,
    teacher_no: r.teacher.teacherNo, teacher_name: r.teacher.name, specialty: r.teacher.specialty,
    phone: r.teacher.phone, teacher_status: r.teacher.teacherStatus, teaching_status: r.teacher.teachingStatus,
    relation_type: r.relation.relationType, created_at: r.relation.createdAt.toISOString() }));
}

export async function classView(row: typeof classes.$inferSelect): Promise<ClassItem> {
  const assignments = await db.select({ relation: relations, teacher: teachers }).from(relations)
    .innerJoin(teachers, eq(teachers.id, relations.teacherId))
    .where(and(eq(relations.classId, row.id), eq(relations.isDeleted, 0), eq(teachers.isDeleted, 0))).orderBy(asc(relations.id));
  const [{ n }] = await db.select({ n: count() }).from(students).where(and(eq(students.classId, row.id), eq(students.isDeleted, 0)));
  return { id: row.id, class_no: row.classNo, class_name: row.className,
    start_date: row.startDate, completion_date: row.completionDate, class_status: row.classStatus,
    total_students: Number(n),
    head_teacher: assignments.find((a) => a.relation.relationType === "班主任") ? teacherView(assignments.find((a) => a.relation.relationType === "班主任")!.teacher) : null,
    teachers: assignments.filter((a) => a.relation.relationType === "授课老师").map((a) => teacherView(a.teacher)) };
}

async function lockAvailableTeacher(tx: Transaction, id: number) {
  const [teacher] = await tx.select().from(teachers).where(and(eq(teachers.id, id), eq(teachers.isDeleted, 0))).for("update");
  if (!teacher) throw new AssignmentError(404, "老师不存在或已删除");
  if (teacher.teacherStatus !== "在职" || teacher.teachingStatus !== "可授课") throw new AssignmentError(409, `${teacher.name} 当前${teacher.teacherStatus} / ${teacher.teachingStatus}，不能安排授课`);
  return teacher;
}

// 铁律 1：老师在未结课班级上只要有任何有效关系（不管什么角色），就算被占用。
// 已结课班级的历史关系不算占用。返回占用记录，空闲返回 null。
async function findBusyRelation(tx: Transaction, teacherId: number) {
  const [busy] = await tx.select({ classId: relations.classId, role: relations.relationType, no: classes.classNo, name: classes.className }).from(relations)
    .innerJoin(classes, eq(classes.id, relations.classId))
    .where(and(eq(relations.teacherId, teacherId), eq(relations.isDeleted, 0), eq(classes.isDeleted, 0), ne(classes.classStatus, "已结课"))).limit(1);
  return busy ?? null;
}

async function createClass(request: Request) {
  const body = await readJson(request);
  if (!body) return jsonErr(422, "请求体必须是 JSON 对象");
  const classNo = asString(body.class_no);
  const name = asString(body.class_name);
  const start = asString(body.start_date);
  const completion = body.completion_date ? asString(body.completion_date) : null;
  const status = asString(body.class_status) || "在读";
  const headId = body.head_teacher_id == null || body.head_teacher_id === "" ? null : asNumber(body.head_teacher_id);
  const lecturerIds = body.teacher_ids ?? [];
  if (!classNo || classNo.length > 30 || !name || name.length > 100 || !start) return jsonErr(422, "班级编号、名称和开班日期必填");
  if (completion && completion < start) return jsonErr(422, "结课日期不能早于开班日期");
  if (!["未开班", "在读", "已结课"].includes(status)) return jsonErr(422, "班级状态不合法");
  if (headId !== null && (!Number.isInteger(headId) || headId! < 1)) return jsonErr(422, "班主任 ID 不合法");
  if (!Array.isArray(lecturerIds) || lecturerIds.some((id) => !Number.isInteger(id) || id < 1)) return jsonErr(422, "任课老师 ID 必须是正整数数组");
  // 铁律 2：新建班级时班主任和任课老师不能是同一人。
  if (headId != null && (lecturerIds as number[]).includes(headId)) return jsonErr(422, "班主任和授课老师不能是同一人");
  if (status === "已结课" && (headId || lecturerIds.length)) return jsonErr(409, "已结课班级不能新增排班，请先按历史班级建立档案");
  const [existing] = await db.select({ id: classes.id }).from(classes).where(eq(classes.classNo, classNo)).limit(1);
  if (existing) return jsonErr(409, "班级编号已存在");
  const newClass = await db.transaction(async (tx) => {
    const ids = [...new Set([...(headId ? [headId] : []), ...(lecturerIds as number[])])].sort((a, b) => a - b);
    for (const id of ids) {
      await lockAvailableTeacher(tx, id);
      // 铁律 1：每位老师都必须当前空闲（未在其他未结课班级任职）。
      const busy = await findBusyRelation(tx, id);
      if (busy) throw new AssignmentError(409, `老师已负责未结课班级 ${busy.no}，一个老师同一时间只能负责一个班级`);
    }
    const [row] = await tx.insert(classes).values({ classNo, className: name, startDate: start, completionDate: completion, classStatus: status }).returning();
    if (headId) await tx.insert(relations).values({ classId: row.id, teacherId: headId, relationType: "班主任" });
    for (const id of new Set(lecturerIds as number[])) await tx.insert(relations).values({ classId: row.id, teacherId: id, relationType: "授课老师" });
    return row;
  });
  return jsonOk(await classView(newClass), 201);
}

async function classOverview(id: number) {
  const [cls] = await db.select().from(classes).where(and(eq(classes.id, id), eq(classes.isDeleted, 0))).limit(1);
  if (!cls) return jsonErr(404, "班级不存在或已删除");
  const genderRows = await db.select({ gender: students.gender, n: count() }).from(students)
    .where(and(eq(students.classId, id), eq(students.isDeleted, 0))).groupBy(students.gender);
  const genders = Object.fromEntries(genderRows.map((r) => [r.gender, Number(r.n)]));
  const [result] = await db.select({ total: count(), graded: sql<number>`count(distinct ${scores.studentId})`,
    passed: sql<number>`count(*) filter (where ${scores.score} >= 60)`, average: sql<string | null>`round(avg(${scores.score}), 2)` })
    .from(scores).innerJoin(students, eq(students.id, scores.studentId))
    .where(and(eq(scores.isDeleted, 0), eq(students.isDeleted, 0), eq(students.classId, id)));
  const qualified = await db.select({ id: scores.studentId }).from(scores).innerJoin(students, eq(students.id, scores.studentId))
    .where(and(eq(scores.isDeleted, 0), eq(students.isDeleted, 0), eq(students.classId, id)))
    .groupBy(scores.studentId).having(sql`min(${scores.score}) >= 80`);
  const [employed] = await db.select({ n: sql<number>`count(distinct ${employmentRecords.studentId})` }).from(employmentRecords)
    .innerJoin(students, eq(students.id, employmentRecords.studentId))
    .where(and(eq(employmentRecords.isDeleted, 0), eq(students.isDeleted, 0), eq(employmentRecords.classNoSnapshot, cls.classNo)));
  const info = await classView(cls);
  return jsonOk({ class_info: info, total_students: info.total_students,
    male_count: genders["男"] || 0, female_count: genders["女"] || 0, other_count: genders["其他"] || 0,
    graded_students: Number(result.graded), total_scores: Number(result.total), passing_scores: Number(result.passed),
    pass_rate: Number(result.total) ? (Number(result.passed) * 100 / Number(result.total)).toFixed(1) : null,
    average_score: result.average, qualified_students: qualified.length, employed_students: Number(employed.n) });
}

async function assign(classId: number, teacherId: number, request: Request) {
  const body = await readJson(request);
  if (!body) return jsonErr(422, "请输入角色");
  const role = asString(body.relation_type) || "授课老师";
  if (!["班主任", "授课老师"].includes(role)) return jsonErr(422, "角色只能为班主任或授课老师");
  const [cls] = await db.select().from(classes).where(and(eq(classes.id, classId), eq(classes.isDeleted, 0))).limit(1);
  if (!cls) return jsonErr(404, "班级不存在或已删除");
  const row = await db.transaction(async (tx) => {
    // 相同老师行锁串行化分配，防止并发把一个老师分到两个班级。
    await lockAvailableTeacher(tx, teacherId);
    const [exist] = await tx.select().from(relations).where(and(eq(relations.classId, classId), eq(relations.teacherId, teacherId), eq(relations.relationType, role), eq(relations.isDeleted, 0))).limit(1);
    if (exist) return exist;
    const [lockedClass] = await tx.select().from(classes).where(eq(classes.id, classId)).for("update");
    if (lockedClass.isDeleted || lockedClass.classStatus === "已结课") throw new AssignmentError(409, "已删除或已结课班级不能新增排班");
    // 铁律 1 + 铁律 2：老师被占用时分两种情况给提示。
    const busy = await findBusyRelation(tx, teacherId);
    if (busy) {
      if (busy.classId === classId) throw new AssignmentError(409, "班主任和授课老师不能是同一人");
      throw new AssignmentError(409, `该老师已负责未结课班级 ${busy.no}，一个老师同一时间只能负责一个班级`);
    }
    // 铁律 3：班主任还要检查这个班是不是已经有班主任了。
    if (role === "班主任") {
      const [head] = await tx.select().from(relations).where(and(eq(relations.classId, classId), eq(relations.relationType, "班主任"), eq(relations.isDeleted, 0))).limit(1);
      if (head) throw new AssignmentError(409, "该班级已有班主任，请先解除原关系再分配");
    }
    const [created] = await tx.insert(relations).values({ classId, teacherId, relationType: role }).returning();
    return created;
  });
  return jsonOk({ id: row.id, class_id: row.classId, teacher_id: row.teacherId, relation_type: row.relationType, created_at: row.createdAt });
}

export async function handleClassManagement(method: string, slug: string[], request: Request): Promise<Response | null> {
  const path = slug.join("/");
  const url = new URL(request.url);
  const { page, pageSize } = readPage(url);
  try {
    if (path === "classes" && method === "POST") return await createClass(request);
    if (path === "classes" && method === "GET") {
      const filters = [eq(classes.isDeleted, 0)];
      const no = url.searchParams.get("class_no");
      const name = url.searchParams.get("class_name");
      const status = url.searchParams.get("class_status");
      if (no) filters.push(eq(classes.classNo, no));
      if (name) filters.push(like(classes.className, `%${name}%`));
      if (status) filters.push(eq(classes.classStatus, status));
      const where = and(...filters);
      const [{ total }] = await db.select({ total: count() }).from(classes).where(where);
      const rows = await db.select().from(classes).where(where).orderBy(asc(classes.id)).limit(pageSize).offset((page - 1) * pageSize);
      return jsonOk(pageData(await Promise.all(rows.map(classView)), Number(total), page, pageSize));
    }
    if (slug[0] === "classes" && slug.length === 2 && method === "GET") {
      const [row] = await db.select().from(classes).where(and(eq(classes.id, Number(slug[1])), eq(classes.isDeleted, 0))).limit(1);
      return row ? jsonOk(await classView(row)) : jsonErr(404, "班级不存在或已删除");
    }
    if (slug[0] === "classes" && slug[2] === "overview" && method === "GET") return await classOverview(Number(slug[1]));
    if (path === "class-teacher-relations" && method === "GET") {
      const classId = url.searchParams.get("class_id");
      const teacherId = url.searchParams.get("teacher_id");
      const role = url.searchParams.get("relation_type");
      let rows = await relationRows(classId ? Number(classId) : undefined, teacherId ? Number(teacherId) : undefined);
      if (role) rows = rows.filter((r) => r.relation_type === role);
      return jsonOk(pageData(rows.slice((page - 1) * pageSize, page * pageSize), rows.length, page, pageSize));
    }
    if (slug[0] === "classes" && slug[2] === "teachers" && slug.length === 4 && method === "PUT") return await assign(Number(slug[1]), Number(slug[3]), request);
    if (slug[0] === "classes" && slug.length === 2 && method === "PATCH") {
      const body = await readJson(request);
      if (!body) return jsonErr(422, "请求体必须是 JSON");
      const id = Number(slug[1]);
      const [old] = await db.select().from(classes).where(and(eq(classes.id, id), eq(classes.isDeleted, 0))).limit(1);
      if (!old) return jsonErr(404, "班级不存在或已删除");
      const patch: Partial<typeof classes.$inferInsert> = { updatedAt: new Date() };
      if ("class_name" in body) { if (!asString(body.class_name)) return jsonErr(422, "名称不能为空"); patch.className = asString(body.class_name); }
      if ("start_date" in body) { if (!asString(body.start_date)) return jsonErr(422, "开班日期不能为空"); patch.startDate = asString(body.start_date); }
      if ("completion_date" in body) patch.completionDate = body.completion_date ? asString(body.completion_date) : null;
      if ("class_status" in body) { if (!["在读", "已结课", "未开班"].includes(String(body.class_status))) return jsonErr(422, "状态不合法"); patch.classStatus = String(body.class_status); }
      const end = patch.completionDate !== undefined ? patch.completionDate : old.completionDate;
      if (end && end < (patch.startDate ?? old.startDate)) return jsonErr(400, "结课日期不能早于开班日期");
      const updated = await db.transaction(async (tx) => {
        // 已结课班级重新开班时，它名下所有老师都不能正被别的未结课班级占用。
        if (old.classStatus === "已结课" && patch.classStatus && patch.classStatus !== "已结课") {
          const links = await tx.select().from(relations).where(and(eq(relations.classId, id), eq(relations.isDeleted, 0)));
          for (const link of links) {
            await lockAvailableTeacher(tx, link.teacherId);
            const busy = await findBusyRelation(tx, link.teacherId);
            if (busy) throw new AssignmentError(409, "该班级有老师已在其他未结课班级任职，请先解除后再重新开班");
          }
        }
        const [row] = await tx.update(classes).set(patch).where(eq(classes.id, id)).returning();
        return row;
      });
      return jsonOk(await classView(updated));
    }
    if (path === "teachers" && method === "GET") {
      const filters = [eq(teachers.isDeleted, 0)];
      for (const [param, column] of [["teacher_no", teachers.teacherNo], ["teacher_status", teachers.teacherStatus], ["teaching_status", teachers.teachingStatus]] as const) {
        const value = url.searchParams.get(param); if (value) filters.push(eq(column, value));
      }
      if (url.searchParams.get("name")) filters.push(like(teachers.name, `%${url.searchParams.get("name")}%`));
      if (url.searchParams.get("specialty")) filters.push(like(teachers.specialty, `%${url.searchParams.get("specialty")}%`));
      const [{ total }] = await db.select({ total: count() }).from(teachers).where(and(...filters));
      const rows = await db.select().from(teachers).where(and(...filters)).orderBy(asc(teachers.id)).limit(pageSize).offset((page - 1) * pageSize);
      return jsonOk(pageData(rows.map(teacherView), Number(total), page, pageSize));
    }
    if (slug[0] === "teachers" && slug.length === 2 && method === "GET") {
      const id = Number(slug[1]);
      const [row] = await db.select().from(teachers).where(and(eq(teachers.id, id), eq(teachers.isDeleted, 0))).limit(1);
      return row ? jsonOk({ ...teacherView(row), relations: await relationRows(undefined, id) }) : jsonErr(404, "老师不存在或已删除");
    }
    if (slug[0] === "teachers" && slug.length === 2 && method === "PATCH" && request.headers.get("content-type")?.includes("json")) {
      const body = await readJson(request.clone());
      // 带授课状态的修改独立处理，原有字段的兼容请求继续由已有路由处理。
      if (body && "teaching_status" in body) {
        const id = Number(slug[1]);
        const [row] = await db.select().from(teachers).where(and(eq(teachers.id, id), eq(teachers.isDeleted, 0))).limit(1);
        if (!row) return jsonErr(404, "老师不存在或已删除");
        if (!["可授课", "暂停授课"].includes(String(body.teaching_status))) return jsonErr(422, "授课状态不合法");
        const patch: Partial<typeof teachers.$inferInsert> = { teachingStatus: String(body.teaching_status), updatedAt: new Date() };
        if ("name" in body) { if (!asString(body.name)) return jsonErr(422, "姓名不能为空"); patch.name = asString(body.name); }
        if ("phone" in body) patch.phone = asString(body.phone) || null;
        if ("contact_info" in body) patch.contactInfo = asString(body.contact_info) || null;
        if ("specialty" in body) patch.specialty = asString(body.specialty) || null;
        if ("gender" in body) patch.gender = asString(body.gender) || null;
        if ("teaching_years" in body) { const years = asNumber(body.teaching_years); if (years === undefined || years < 0) return jsonErr(422, "教学年限不合法"); patch.teachingYears = years.toFixed(2); }
        if ("teacher_status" in body) { if (!["在职", "离职"].includes(String(body.teacher_status))) return jsonErr(422, "在职状态不合法"); patch.teacherStatus = String(body.teacher_status); }
        const [updated] = await db.update(teachers).set(patch).where(eq(teachers.id, id)).returning();
        return jsonOk(teacherView(updated));
      }
    }
    return null;
  } catch (error) {
    if (error instanceof AssignmentError) return jsonErr(error.status, error.message);
    throw error;
  }
}
