import { bigint, date, index, integer, numeric, pgTable, smallint, timestamp, varchar } from "drizzle-orm/pg-core";

/** 公共字段：逻辑删除 + 时间戳。普通查询必须过滤 is_deleted = 0。 */
const audit = {
  isDeleted: smallint("is_deleted").notNull().default(0),
  deletedAt: timestamp("deleted_at", { mode: "date" }),
  createdAt: timestamp("created_at", { mode: "date" }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { mode: "date" }).notNull().defaultNow(),
};

/** 班级表 */
export const classes = pgTable(
  "classes",
  {
    id: bigint("id", { mode: "number" }).primaryKey().generatedAlwaysAsIdentity(),
    classNo: varchar("class_no", { length: 30 }).notNull().unique(),
    className: varchar("class_name", { length: 100 }).notNull(),
    startDate: date("start_date", { mode: "string" }).notNull(),
    completionDate: date("completion_date", { mode: "string" }),
    classStatus: varchar("class_status", { length: 20 }).notNull().default("在读"),
    ...audit,
  },
  (t) => [index("idx_classes_status_deleted").on(t.classStatus, t.isDeleted)],
);

/** 老师表：phone 存电话，contact_info 存微信/邮箱 */
export const teachers = pgTable(
  "teachers",
  {
    id: bigint("id", { mode: "number" }).primaryKey().generatedAlwaysAsIdentity(),
    teacherNo: varchar("teacher_no", { length: 30 }).notNull().unique(),
    name: varchar("name", { length: 50 }).notNull(),
    gender: varchar("gender", { length: 10 }),
    specialty: varchar("specialty", { length: 100 }),
    phone: varchar("phone", { length: 30 }),
    contactInfo: varchar("contact_info", { length: 150 }),
    teachingYears: numeric("teaching_years", { precision: 5, scale: 2 }).notNull().default("0"),
    teacherStatus: varchar("teacher_status", { length: 20 }).notNull().default("在职"),
    teachingStatus: varchar("teaching_status", { length: 20 }).notNull().default("可授课"),
    ...audit,
  },
  (t) => [index("idx_teachers_name_deleted").on(t.name, t.isDeleted)],
);

/** 学生表：只存出生日期，年龄动态计算 */
export const students = pgTable(
  "students",
  {
    id: bigint("id", { mode: "number" }).primaryKey().generatedAlwaysAsIdentity(),
    studentNo: varchar("student_no", { length: 30 }).notNull().unique(),
    classId: bigint("class_id", { mode: "number" }).notNull(),
    name: varchar("name", { length: 50 }).notNull(),
    hometown: varchar("hometown", { length: 100 }),
    graduateSchool: varchar("graduate_school", { length: 150 }),
    major: varchar("major", { length: 100 }),
    trainingEnrollmentDate: date("training_enrollment_date", { mode: "string" }),
    trainingGraduationDate: date("training_graduation_date", { mode: "string" }),
    education: varchar("education", { length: 30 }),
    consultantNo: varchar("consultant_no", { length: 30 }),
    birthDate: date("birth_date", { mode: "string" }).notNull(),
    gender: varchar("gender", { length: 10 }).notNull(),
    avatarUrl: varchar("avatar_url", { length: 500 }),
    ...audit,
  },
  (t) => [
    index("idx_students_class_deleted").on(t.classId, t.isDeleted),
    index("idx_students_name_deleted").on(t.name, t.isDeleted),
    index("idx_students_birth_deleted").on(t.birthDate, t.isDeleted),
  ],
);

/** 考核成绩：业务定位键是 student_id + exam_no，不是自增 id */
export const scores = pgTable(
  "scores",
  {
    id: bigint("id", { mode: "number" }).primaryKey().generatedAlwaysAsIdentity(),
    studentId: bigint("student_id", { mode: "number" }).notNull(),
    examNo: integer("exam_no").notNull(),
    score: numeric("score", { precision: 5, scale: 2 }).notNull(),
    ...audit,
  },
  (t) => [index("idx_scores_student_deleted_exam").on(t.studentId, t.isDeleted, t.examNo)],
);

/** 学生过往经历：一名学生多条 */
export const pastExperiences = pgTable(
  "student_past_experiences",
  {
    id: bigint("id", { mode: "number" }).primaryKey().generatedAlwaysAsIdentity(),
    studentId: bigint("student_id", { mode: "number" }).notNull(),
    pastSalaryAmount: numeric("past_salary_amount", { precision: 12, scale: 2 }),
    pastSalaryPeriod: varchar("past_salary_period", { length: 10 }),
    workYears: numeric("work_years", { precision: 5, scale: 2 }).notNull().default("0"),
    graduationDate: date("graduation_date", { mode: "string" }),
    intendedCity: varchar("intended_city", { length: 100 }),
    previousPosition: varchar("previous_position", { length: 100 }),
    ...audit,
  },
  (t) => [index("idx_past_exp_student_deleted").on(t.studentId, t.isDeleted)],
);

/** 就业记录：一名学生多条历史，快照字段创建时写入 */
export const employmentRecords = pgTable(
  "employment_records",
  {
    id: bigint("id", { mode: "number" }).primaryKey().generatedAlwaysAsIdentity(),
    studentId: bigint("student_id", { mode: "number" }).notNull(),
    studentNameSnapshot: varchar("student_name_snapshot", { length: 50 }).notNull(),
    classNoSnapshot: varchar("class_no_snapshot", { length: 30 }).notNull(),
    employmentOpenDate: date("employment_open_date", { mode: "string" }),
    offerDate: date("offer_date", { mode: "string" }),
    companyName: varchar("company_name", { length: 150 }).notNull(),
    employmentCity: varchar("employment_city", { length: 100 }),
    position: varchar("position", { length: 100 }),
    salaryAmount: numeric("salary_amount", { precision: 12, scale: 2 }).notNull(),
    salaryPeriod: varchar("salary_period", { length: 10 }).notNull(),
    // 就业前快照：只在新增时从过往经历复制，之后不随学生档案改变。
    pastSalaryAmount: numeric("past_salary_amount", { precision: 12, scale: 2 }),
    pastSalaryPeriod: varchar("past_salary_period", { length: 10 }),
    previousPosition: varchar("previous_position", { length: 100 }),
    pastGraduationDate: date("past_graduation_date", { mode: "string" }),
    ...audit,
  },
  (t) => [index("idx_emp_student_deleted").on(t.studentId, t.isDeleted)],
);

/** 班级老师关系：班主任 / 授课老师 */
export const classTeacherRelations = pgTable(
  "class_teacher_relations",
  {
    id: bigint("id", { mode: "number" }).primaryKey().generatedAlwaysAsIdentity(),
    classId: bigint("class_id", { mode: "number" }).notNull(),
    teacherId: bigint("teacher_id", { mode: "number" }).notNull(),
    relationType: varchar("relation_type", { length: 30 }).notNull().default("授课老师"),
    ...audit,
  },
  (t) => [index("idx_ctr_class_deleted").on(t.classId, t.isDeleted)],
);
