import { and, asc, count, desc, eq, like, ne, or, sql } from "drizzle-orm";
import { db } from "@/db";
import { classes, employmentRecords as records, pastExperiences, students } from "@/db/schema";
import { annualized, calculateAge } from "@/lib/age";
import { asNumber, asString, jsonErr, jsonOk, pageData, readJson, readPage } from "@/lib/http";
import type { Employment, SalaryComparison } from "@/lib/contracts";

function view(row: typeof records.$inferSelect, studentNo?: string, classId?: number | null): Employment {
  return {
    id: row.id, student_id: row.studentId, student_no: studentNo, class_id: classId,
    student_name_snapshot: row.studentNameSnapshot, class_no_snapshot: row.classNoSnapshot,
    employment_open_date: row.employmentOpenDate, offer_date: row.offerDate,
    company_name: row.companyName, employment_city: row.employmentCity, position: row.position,
    salary_amount: Number(row.salaryAmount).toFixed(2), salary_period: row.salaryPeriod,
    offer_status: row.offerStatus,
    annualized_salary: annualized(row.salaryAmount, row.salaryPeriod),
    past_salary_amount: row.pastSalaryAmount == null ? null : Number(row.pastSalaryAmount).toFixed(2),
    past_salary_period: row.pastSalaryPeriod, previous_position: row.previousPosition,
    past_graduation_date: row.pastGraduationDate,
    graduation_years: row.pastGraduationDate ? calculateAge(row.pastGraduationDate) : null,
    created_at: row.createdAt.toISOString(), updated_at: row.updatedAt.toISOString(),
  };
}

export function salaryComparison(row: typeof records.$inferSelect): SalaryComparison {
  const before = row.pastSalaryAmount == null || !row.pastSalaryPeriod ? null : Number(annualized(row.pastSalaryAmount, row.pastSalaryPeriod));
  const after = Number(annualized(row.salaryAmount, row.salaryPeriod));
  return {
    employment_record_id: row.id, student_id: row.studentId, student_name_snapshot: row.studentNameSnapshot,
    previous_position: row.previousPosition, position: row.position,
    past_salary_amount: row.pastSalaryAmount, past_salary_period: row.pastSalaryPeriod,
    salary_amount: row.salaryAmount, salary_period: row.salaryPeriod,
    past_annualized_salary: before === null ? null : before.toFixed(2), annualized_salary: after.toFixed(2),
    monthly_before: before === null ? null : (before / 12).toFixed(2), monthly_after: (after / 12).toFixed(2),
    annual_increase: before === null ? null : (after - before).toFixed(2),
    increase_percent: before === null || before === 0 ? null : ((after - before) * 100 / before).toFixed(1),
    comparison_available: before !== null,
  };
}

async function createEmployment(request: Request) {
  const body = await readJson(request);
  if (!body) return jsonErr(422, "请求体必须是 JSON");
  const studentId = asNumber(body.student_id);
  const company = asString(body.company_name);
  const amount = asNumber(body.salary_amount);
  const period = asString(body.salary_period);
  if (!studentId || !company || amount === undefined || !period) return jsonErr(422, "学生、公司、金额和周期必填");
  if (amount < 0 || amount > 9999999999.99 || !["MONTH", "YEAR"].includes(period)) return jsonErr(422, "薪资不能为负且周期只能为 MONTH/YEAR");
  const openDate = asString(body.employment_open_date) || null;
  const offerDate = asString(body.offer_date) || null;
  if (offerDate && !openDate) return jsonErr(422, "就业尚未开放，填写 Offer 日期之前请先填写就业开放日期");
  if (openDate && offerDate && offerDate < openDate) return jsonErr(422, "Offer 日期不能早于就业开放日期");
  const [student] = await db.select().from(students).where(and(eq(students.id, studentId), eq(students.isDeleted, 0))).limit(1);
  if (!student) return jsonErr(404, "学生不存在或已删除");
  // 规则：学生结课后才能登记就业信息
  if (!student.trainingGraduationDate) return jsonErr(400, "该学生尚未结课，不能新增就业信息");
  // 规则：就业开放日期必须大于等于学生的培训结课日期
  if (openDate && openDate < student.trainingGraduationDate) return jsonErr(400, "就业开放日期不能早于学生培训结课日期");
  const [cls] = await db.select().from(classes).where(and(eq(classes.id, student.classId), eq(classes.isDeleted, 0))).limit(1);
  if (!cls) return jsonErr(404, "学生所属班级不存在或已删除");
  const [previous] = await db.select().from(pastExperiences).where(and(eq(pastExperiences.studentId, studentId), eq(pastExperiences.isDeleted, 0))).orderBy(desc(pastExperiences.id)).limit(1);
  // 未提交时自动取最近过往经历；显式 null 表示不采用历史金额。快照只复制一次。
  const oldAmount = "past_salary_amount" in body ? (body.past_salary_amount == null || body.past_salary_amount === "" ? null : asNumber(body.past_salary_amount)) : previous?.pastSalaryAmount == null ? null : Number(previous.pastSalaryAmount);
  const oldPeriod = "past_salary_period" in body ? asString(body.past_salary_period) || null : previous?.pastSalaryPeriod ?? null;
  if (oldAmount === undefined || (oldAmount !== null && (!oldPeriod || oldAmount < 0 || oldAmount > 9999999999.99))) return jsonErr(422, "以往薪资非负且必须搭配薪资周期");
  if (oldPeriod && !["MONTH", "YEAR"].includes(oldPeriod)) return jsonErr(422, "以往薪资周期不合法");
  const grad = "past_graduation_date" in body ? asString(body.past_graduation_date) || null : previous?.graduationDate ?? null;
  if (grad && grad > new Date().toISOString().slice(0, 10)) return jsonErr(422, "学历毕业日期不能晚于今天");
  const [row] = await db.insert(records).values({
    studentId, studentNameSnapshot: student.name, classNoSnapshot: cls.classNo,
    employmentOpenDate: openDate, offerDate, companyName: company,
    employmentCity: asString(body.employment_city) || null, position: asString(body.position) || null,
    salaryAmount: amount.toFixed(2), salaryPeriod: period,
    pastSalaryAmount: oldAmount === null ? null : oldAmount.toFixed(2), pastSalaryPeriod: oldPeriod,
    previousPosition: "previous_position" in body ? asString(body.previous_position) || null : previous?.previousPosition ?? null,
    pastGraduationDate: grad,
  }).returning();
  return jsonOk(view(row, student.studentNo, cls.id), 201);
}

export async function handleEmploymentManagement(method: string, slug: string[], request: Request): Promise<Response | null> {
  const path = slug.join("/");
  const url = new URL(request.url);
  const { page, pageSize } = readPage(url);
  if (path === "employment-records/options" && method === "GET") {
    const cities = await db.selectDistinct({ value: records.employmentCity }).from(records).innerJoin(students, eq(students.id, records.studentId))
      .where(and(eq(records.isDeleted, 0), eq(students.isDeleted, 0))).orderBy(asc(records.employmentCity));
    const positions = await db.selectDistinct({ value: records.position }).from(records).innerJoin(students, eq(students.id, records.studentId))
      .where(and(eq(records.isDeleted, 0), eq(students.isDeleted, 0))).orderBy(asc(records.position));
    return jsonOk({ cities: cities.map((r) => r.value).filter(Boolean), positions: positions.map((r) => r.value).filter(Boolean) });
  }
  if (path === "employment-records" && method === "POST") return createEmployment(request);
  // 接受 / 拒绝 Offer：接受一条，同一学生其它记录自动改为已拒绝
  if (slug[0] === "employment-records" && slug.length === 3 && (slug[2] === "accept" || slug[2] === "reject") && method === "POST") {
    const id = Number(slug[1]);
    const [row] = await db.select().from(records).where(and(eq(records.id, id), eq(records.isDeleted, 0))).limit(1);
    if (!row) return jsonErr(404, "就业记录不存在或已删除");
    const status = slug[2] === "accept" ? "已接受" : "已拒绝";
    const [updated] = await db.update(records).set({ offerStatus: status, updatedAt: new Date() }).where(eq(records.id, id)).returning();
    if (slug[2] === "accept") {
      // 选中这条之后，同学生其它未删除记录全部改为已拒绝（记录保留，不删除）
      await db.update(records).set({ offerStatus: "已拒绝", updatedAt: new Date() })
        .where(and(eq(records.studentId, updated.studentId), ne(records.id, id), eq(records.isDeleted, 0)));
    }
    return jsonOk(view(updated));
  }
  const individual = slug[0] === "employment-records" && (slug.length === 2 || (slug.length === 3 && slug[2] === "comparison"));
  if (individual && /^\d+$/.test(slug[1]) && method === "GET") {
    const [result] = await db.select({ record: records, studentNo: students.studentNo, classId: classes.id })
      .from(records).innerJoin(students, eq(students.id, records.studentId))
      .leftJoin(classes, eq(classes.classNo, records.classNoSnapshot))
      .where(and(eq(records.id, Number(slug[1])), eq(records.isDeleted, 0), eq(students.isDeleted, 0))).limit(1);
    if (!result) return jsonErr(404, "就业记录不存在或所属学生已删除");
    return jsonOk(slug[2] === "comparison" ? salaryComparison(result.record) : view(result.record, result.studentNo, result.classId));
  }
  if (individual && slug.length === 2 && method === "PATCH") {
    const body = await readJson(request.clone());
    if (!body) return jsonErr(422, "请求体必须是 JSON");
    if (["past_salary_amount", "past_salary_period", "previous_position", "past_graduation_date"].some((key) => key in body)) {
      const [row] = await db.select({ r: records }).from(records).innerJoin(students, eq(students.id, records.studentId))
        .where(and(eq(records.id, Number(slug[1])), eq(records.isDeleted, 0), eq(students.isDeleted, 0))).limit(1);
      if (!row) return jsonErr(404, "就业记录不存在或已删除");
      const patch: Partial<typeof records.$inferInsert> = { updatedAt: new Date() };
      if ("past_salary_amount" in body) { const n = body.past_salary_amount == null ? null : asNumber(body.past_salary_amount); if (n === undefined || (n !== null && n < 0)) return jsonErr(422, "以往薪资不合法"); patch.pastSalaryAmount = n === null ? null : n.toFixed(2); }
      if ("past_salary_period" in body) { if (body.past_salary_period !== null && !["MONTH", "YEAR"].includes(String(body.past_salary_period))) return jsonErr(422, "周期不合法"); patch.pastSalaryPeriod = body.past_salary_period as string | null; }
      if ("previous_position" in body) patch.previousPosition = asString(body.previous_position) || null;
      if ("past_graduation_date" in body) patch.pastGraduationDate = asString(body.past_graduation_date) || null;
      const past = patch.pastSalaryAmount !== undefined ? patch.pastSalaryAmount : row.r.pastSalaryAmount;
      const pastPeriod = patch.pastSalaryPeriod !== undefined ? patch.pastSalaryPeriod : row.r.pastSalaryPeriod;
      if (past !== null && !pastPeriod) return jsonErr(400, "填写以往薪资时必须提供周期");
      for (const [key, column] of [["company_name", "companyName"], ["employment_city", "employmentCity"], ["position", "position"], ["employment_open_date", "employmentOpenDate"], ["offer_date", "offerDate"]] as const) {
        if (key in body) {
          if (key === "company_name" && !asString(body[key])) return jsonErr(422, "公司名称不能为空");
          const val = asString(body[key]) || null;
          if (column === "companyName") patch.companyName = val!;
          else patch[column] = val;
        }
      }
      if ("salary_amount" in body) { const n = asNumber(body.salary_amount); if (n === undefined || n < 0) return jsonErr(422, "薪资不合法"); patch.salaryAmount = n.toFixed(2); }
      if ("salary_period" in body) { if (!["MONTH", "YEAR"].includes(String(body.salary_period))) return jsonErr(422, "薪资周期不合法"); patch.salaryPeriod = String(body.salary_period); }
      const open = patch.employmentOpenDate !== undefined ? patch.employmentOpenDate : row.r.employmentOpenDate;
      const offer = patch.offerDate !== undefined ? patch.offerDate : row.r.offerDate;
      if (offer && !open) return jsonErr(400, "就业尚未开放，填写 Offer 日期之前请先填写就业开放日期");
      if (open && offer && offer < open) return jsonErr(400, "Offer 日期不能早于就业开放日期");
      const [updated] = await db.update(records).set(patch).where(eq(records.id, row.r.id)).returning();
      return jsonOk(view(updated));
    }
    return null;
  }
  const byStudent = slug[0] === "students" && slug[2] === "employment-records" && slug.length === 3;
  const byClass = slug[0] === "classes" && slug[2] === "employment-records" && slug.length === 3;
  if (method !== "GET" || !(path === "employment-records" || byStudent || byClass)) return null;
  const filters = [eq(records.isDeleted, 0), eq(students.isDeleted, 0)];
  if (byStudent) {
    const [s] = await db.select().from(students).where(and(eq(students.id, Number(slug[1])), eq(students.isDeleted, 0))).limit(1);
    if (!s) return jsonErr(404, "学生不存在或已删除");
    filters.push(eq(records.studentId, s.id));
  }
  const classId = byClass ? slug[1] : url.searchParams.get("class_id");
  if (classId) {
    const [cls] = await db.select().from(classes).where(and(eq(classes.id, Number(classId)), eq(classes.isDeleted, 0))).limit(1);
    if (!cls) return byClass ? jsonErr(404, "班级不存在或已删除") : jsonOk(pageData([], 0, page, pageSize));
    filters.push(eq(records.classNoSnapshot, cls.classNo));
  }
  const q = url.searchParams.get("q");
  if (q) filters.push(or(like(students.studentNo, `%${q}%`), like(records.studentNameSnapshot, `%${q}%`), like(records.companyName, `%${q}%`))!);
  if (url.searchParams.get("student_no")) filters.push(eq(students.studentNo, url.searchParams.get("student_no")!));
  for (const [key, col] of [["employment_city", records.employmentCity], ["position", records.position], ["company_name", records.companyName]] as const) {
    const value = url.searchParams.get(key); if (value) filters.push(like(col, `%${value}%`));
  }
  const basis = url.searchParams.get("salary_basis");
  const annual = sql`case when ${records.salaryPeriod} = 'MONTH' then ${records.salaryAmount} * 12 else ${records.salaryAmount} end`;
  const salary = basis === "MONTH" ? sql`(${annual}) / 12` : basis === "YEAR" ? annual : sql`${records.salaryAmount}`;
  if (url.searchParams.get("salary_period")) filters.push(eq(records.salaryPeriod, url.searchParams.get("salary_period")!));
  for (const [minKey, maxKey, expression] of [["min_salary", "max_salary", salary], ["min_annualized_salary", "max_annualized_salary", annual]] as const) {
    const lower = url.searchParams.get(minKey); const upper = url.searchParams.get(maxKey);
    if ((lower !== null && (!Number.isFinite(Number(lower)) || Number(lower) < 0)) || (upper !== null && (!Number.isFinite(Number(upper)) || Number(upper) < 0))) return jsonErr(422, "薪资区间必须是非负数");
    if (lower !== null && upper !== null && Number(lower) > Number(upper)) return jsonErr(422, "最低薪资不能大于最高薪资");
    if (lower !== null) filters.push(sql`${expression} >= ${Number(lower)}`);
    if (upper !== null) filters.push(sql`${expression} <= ${Number(upper)}`);
  }
  const years = sql`date_part('year', age(current_date, ${records.pastGraduationDate}))`;
  const minYears = url.searchParams.get("min_graduation_years");
  const maxYears = url.searchParams.get("max_graduation_years");
  if (minYears !== null && (!/^\d+$/.test(minYears) || Number(minYears) > 100)) return jsonErr(422, "毕业年限必须是 0–100 的整数");
  if (maxYears !== null && (!/^\d+$/.test(maxYears) || Number(maxYears) > 100)) return jsonErr(422, "毕业年限必须是 0–100 的整数");
  if (minYears !== null && maxYears !== null && Number(minYears) > Number(maxYears)) return jsonErr(422, "毕业年限区间不合法");
  if (minYears !== null) filters.push(sql`${years} >= ${Number(minYears)}`);
  if (maxYears !== null) filters.push(sql`${years} <= ${Number(maxYears)}`);
  const where = and(...filters);
  const [{ total }] = await db.select({ total: count() }).from(records).innerJoin(students, eq(students.id, records.studentId)).where(where);
  const query = db.select({ record: records, studentNo: students.studentNo, classId: classes.id }).from(records)
    .innerJoin(students, eq(students.id, records.studentId)).leftJoin(classes, eq(classes.classNo, records.classNoSnapshot))
    .where(where).orderBy(byStudent ? asc(records.employmentOpenDate) : desc(records.createdAt), asc(records.id));
  const rows = await query.limit(pageSize).offset((page - 1) * pageSize);
  return jsonOk(pageData(rows.map((r) => view(r.record, r.studentNo, r.classId)), Number(total), page, pageSize));
}
