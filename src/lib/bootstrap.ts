import { sql } from "drizzle-orm";
import { db } from "@/db";
import { classTeacherRelations, classes, employmentRecords, pastExperiences, scores, students, teachers } from "@/db/schema";

// 多个页面同时首屏请求时共用一次初始化，防止重复写入演示数据。
let initialization: Promise<void> | null = null;

const DDL = [
  `CREATE TABLE IF NOT EXISTS classes (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    class_no varchar(30) NOT NULL UNIQUE,
    class_name varchar(100) NOT NULL,
    start_date date NOT NULL,
    completion_date date,
    class_status varchar(20) NOT NULL DEFAULT '在读',
    is_deleted smallint NOT NULL DEFAULT 0,
    deleted_at timestamp,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
  )`,
  `CREATE TABLE IF NOT EXISTS teachers (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    teacher_no varchar(30) NOT NULL UNIQUE,
    name varchar(50) NOT NULL,
    gender varchar(10),
    specialty varchar(100),
    phone varchar(30),
    contact_info varchar(150),
    teaching_years numeric(5,2) NOT NULL DEFAULT 0,
    teacher_status varchar(20) NOT NULL DEFAULT '在职',
    is_deleted smallint NOT NULL DEFAULT 0,
    deleted_at timestamp,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
  )`,
  `CREATE TABLE IF NOT EXISTS students (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_no varchar(30) NOT NULL UNIQUE,
    class_id bigint NOT NULL,
    name varchar(50) NOT NULL,
    hometown varchar(100),
    graduate_school varchar(150),
    major varchar(100),
    training_enrollment_date date,
    training_graduation_date date,
    education varchar(30),
    consultant_no varchar(30),
    birth_date date NOT NULL,
    gender varchar(10) NOT NULL,
    avatar_url varchar(500),
    is_deleted smallint NOT NULL DEFAULT 0,
    deleted_at timestamp,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
  )`,
  `CREATE TABLE IF NOT EXISTS scores (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id bigint NOT NULL,
    exam_no integer NOT NULL,
    score numeric(5,2) NOT NULL,
    is_deleted smallint NOT NULL DEFAULT 0,
    deleted_at timestamp,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
  )`,
  `CREATE TABLE IF NOT EXISTS student_past_experiences (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id bigint NOT NULL,
    past_salary_amount numeric(12,2),
    past_salary_period varchar(10),
    work_years numeric(5,2) NOT NULL DEFAULT 0,
    graduation_date date,
    intended_city varchar(100),
    previous_position varchar(100),
    is_deleted smallint NOT NULL DEFAULT 0,
    deleted_at timestamp,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
  )`,
  `CREATE TABLE IF NOT EXISTS employment_records (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id bigint NOT NULL,
    student_name_snapshot varchar(50) NOT NULL,
    class_no_snapshot varchar(30) NOT NULL,
    employment_open_date date,
    offer_date date,
    company_name varchar(150) NOT NULL,
    employment_city varchar(100),
    position varchar(100),
    salary_amount numeric(12,2) NOT NULL,
    salary_period varchar(10) NOT NULL,
    is_deleted smallint NOT NULL DEFAULT 0,
    deleted_at timestamp,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
  )`,
  `CREATE TABLE IF NOT EXISTS class_teacher_relations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    class_id bigint NOT NULL,
    teacher_id bigint NOT NULL,
    relation_type varchar(30) NOT NULL DEFAULT '授课老师',
    is_deleted smallint NOT NULL DEFAULT 0,
    deleted_at timestamp,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
  )`,
];

const AVATARS = [
  "https://images.pexels.com/photos/8101969/pexels-photo-8101969.jpeg?auto=compress&cs=tinysrgb&w=400",
  "https://images.pexels.com/photos/9490399/pexels-photo-9490399.jpeg?auto=compress&cs=tinysrgb&w=400",
  "https://images.pexels.com/photos/8297057/pexels-photo-8297057.jpeg?auto=compress&cs=tinysrgb&w=400",
  "https://images.pexels.com/photos/5538007/pexels-photo-5538007.jpeg?auto=compress&cs=tinysrgb&w=400",
  "https://images.pexels.com/photos/5538613/pexels-photo-5538613.jpeg?auto=compress&cs=tinysrgb&w=400",
  "https://images.pexels.com/photos/6077567/pexels-photo-6077567.jpeg?auto=compress&cs=tinysrgb&w=400",
];

export async function ensureReady() {
  if (!initialization) {
    initialization = prepareDatabase().catch((error) => {
      initialization = null;
      throw error;
    });
  }
  await initialization;
}

async function prepareDatabase() {
  for (const stmt of DDL) await db.execute(sql.raw(stmt));
  // 增量补字段，不删除或重建业务数据。
  await db.execute(sql`ALTER TABLE teachers ADD COLUMN IF NOT EXISTS teaching_status varchar(20) NOT NULL DEFAULT '可授课'`);
  await db.execute(sql`ALTER TABLE employment_records ADD COLUMN IF NOT EXISTS past_salary_amount numeric(12,2)`);
  await db.execute(sql`ALTER TABLE employment_records ADD COLUMN IF NOT EXISTS past_salary_period varchar(10)`);
  await db.execute(sql`ALTER TABLE employment_records ADD COLUMN IF NOT EXISTS previous_position varchar(100)`);
  await db.execute(sql`ALTER TABLE employment_records ADD COLUMN IF NOT EXISTS past_graduation_date date`);
  // 历史脏数据修复（幂等语句，可重复执行，不删业务数据）：
  // 1) 把空的班级快照从学生当前班级复制补齐
  await db.execute(sql`UPDATE employment_records e SET class_no_snapshot = c.class_no FROM students s JOIN classes c ON c.id = s.class_id WHERE e.student_id = s.id AND e.class_no_snapshot IS NULL`);
  // 2) 同一老师在未结课班级有多条有效关系时只保留最早一条，其余逻辑删除
  await db.execute(sql`UPDATE class_teacher_relations r SET is_deleted = 1, deleted_at = now() WHERE r.is_deleted = 0 AND r.id NOT IN (SELECT MIN(r2.id) FROM class_teacher_relations r2 JOIN classes c ON c.id = r2.class_id WHERE r2.is_deleted = 0 AND c.is_deleted = 0 AND c.class_status <> '已结课' GROUP BY r2.teacher_id) AND EXISTS (SELECT 1 FROM classes c2 WHERE c2.id = r.class_id AND c2.is_deleted = 0 AND c2.class_status <> '已结课')`);
  // 3) 快照列改为必填（前面已补齐空值，这里不会失败）
  await db.execute(sql`ALTER TABLE employment_records ALTER COLUMN class_no_snapshot SET NOT NULL`);
  // 新增字段/新表（幂等，可重复执行）
  await db.execute(sql`ALTER TABLE employment_records ADD COLUMN IF NOT EXISTS offer_status varchar(20) NOT NULL DEFAULT '待处理'`);
  await db.execute(sql`CREATE TABLE IF NOT EXISTS users (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username varchar(50) NOT NULL UNIQUE,
    password_hash varchar(255) NOT NULL,
    display_name varchar(50) NOT NULL,
    role varchar(20) NOT NULL DEFAULT 'viewer',
    class_id bigint,
    token varchar(64),
    is_active smallint NOT NULL DEFAULT 1,
    is_deleted smallint NOT NULL DEFAULT 0,
    deleted_at timestamp,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
  )`);
  const existing = await db.select({ id: classes.id }).from(classes).limit(1);
  if (existing.length === 0) await seedDemo();
}

async function seedDemo() {
  const [c1] = await db
    .insert(classes)
    .values([
      { classNo: "WL2026-A", className: "Python 全栈开发 2026 春季班", startDate: "2026-03-01", classStatus: "在读" },
      { classNo: "WL2026-B", className: "Java 就业冲刺班", startDate: "2026-04-15", classStatus: "在读" },
      { classNo: "WL2025-C", className: "测试开发进阶班", startDate: "2025-09-01", completionDate: "2026-02-28", classStatus: "已结课" },
    ])
    .returning();
  const allClasses = await db.select().from(classes);
  const classA = allClasses.find((c) => c.classNo === "WL2026-A") ?? c1;
  const classB = allClasses.find((c) => c.classNo === "WL2026-B") ?? c1;
  const classC = allClasses.find((c) => c.classNo === "WL2025-C") ?? c1;

  await db.insert(teachers).values([
    { teacherNo: "T001", name: "李明", gender: "男", specialty: "Python 后端", phone: "13800001001", contactInfo: "微信：liming_wl", teachingYears: "8.50", teacherStatus: "在职" },
    { teacherNo: "T002", name: "王芳", gender: "女", specialty: "就业指导 / 简历辅导", phone: "13800001002", contactInfo: "邮箱：wangfang@wolin.edu", teachingYears: "5.00", teacherStatus: "在职" },
    { teacherNo: "T003", name: "赵强", gender: "男", specialty: "Java / 微服务", phone: "13800001003", teachingYears: "10.00", teacherStatus: "在职" },
    { teacherNo: "T004", name: "陈雪", gender: "女", specialty: "前端与 UI", contactInfo: "微信：chenxue_fe", teachingYears: "3.50", teacherStatus: "在职" },
  ]);
  const allTeachers = await db.select().from(teachers);
  const t1 = allTeachers.find((t) => t.teacherNo === "T001")!;
  const t2 = allTeachers.find((t) => t.teacherNo === "T002")!;
  const t3 = allTeachers.find((t) => t.teacherNo === "T003")!;
  const t4 = allTeachers.find((t) => t.teacherNo === "T004")!;

  // 演示排班遵守 3 条铁律：班主任与授课老师是不同的人；每人只负责一个未结课班级。
  // T002 在已结课的 C 班任职不算占用，所以还可以兼任 B 班授课老师。
  await db.insert(classTeacherRelations).values([
    { classId: classA.id, teacherId: t1.id, relationType: "班主任" },
    { classId: classA.id, teacherId: t4.id, relationType: "授课老师" },
    { classId: classB.id, teacherId: t3.id, relationType: "班主任" },
    { classId: classB.id, teacherId: t2.id, relationType: "授课老师" },
    { classId: classC.id, teacherId: t2.id, relationType: "班主任" },
  ]);

  await db.insert(students).values([
    { studentNo: "ST20260001", classId: classA.id, name: "张三", hometown: "江苏南京", graduateSchool: "南京某大学", major: "计算机科学与技术", trainingEnrollmentDate: "2026-03-01", education: "本科", consultantNo: "C001", birthDate: "1994-05-18", gender: "男", avatarUrl: AVATARS[0] },
    { studentNo: "ST20260002", classId: classA.id, name: "李娜", hometown: "浙江杭州", graduateSchool: "杭州某学院", major: "软件工程", trainingEnrollmentDate: "2026-03-01", education: "本科", birthDate: "2002-08-12", gender: "女", avatarUrl: AVATARS[1] },
    { studentNo: "ST20260003", classId: classA.id, name: "王伟", hometown: "安徽合肥", graduateSchool: "合肥工业大学", major: "信息管理", trainingEnrollmentDate: "2026-03-01", education: "本科", birthDate: "1990-11-02", gender: "男", avatarUrl: AVATARS[5] },
    { studentNo: "ST20260004", classId: classB.id, name: "赵敏", hometown: "上海", graduateSchool: "上海某大学", major: "电子信息", trainingEnrollmentDate: "2026-04-15", education: "硕士", birthDate: "1998-01-20", gender: "女", avatarUrl: AVATARS[2] },
    { studentNo: "ST20260005", classId: classB.id, name: "刘洋", hometown: "山东青岛", graduateSchool: "中国海洋大学", major: "自动化", trainingEnrollmentDate: "2026-04-15", education: "本科", birthDate: "2001-03-08", gender: "男", avatarUrl: AVATARS[4] },
    { studentNo: "ST20260006", classId: classB.id, name: "陈晨", hometown: "四川成都", graduateSchool: "电子科技大学", major: "计算机", trainingEnrollmentDate: "2026-04-15", education: "本科", birthDate: "1999-07-30", gender: "其他", avatarUrl: AVATARS[3] },
    { studentNo: "ST20250011", classId: classC.id, name: "周杰", hometown: "湖南长沙", graduateSchool: "中南大学", major: "软件工程", trainingEnrollmentDate: "2025-09-01", trainingGraduationDate: "2026-02-28", education: "本科", birthDate: "1995-12-01", gender: "男", avatarUrl: AVATARS[0] },
    { studentNo: "ST20250012", classId: classC.id, name: "吴雪", hometown: "福建厦门", graduateSchool: "厦门大学", major: "统计学", trainingEnrollmentDate: "2025-09-01", trainingGraduationDate: "2026-02-28", education: "硕士", birthDate: "1993-04-16", gender: "女", avatarUrl: AVATARS[1] },
  ]);

  const allStudents = await db.select().from(students);
  const byNo = Object.fromEntries(allStudents.map((s) => [s.studentNo, s]));

  await db.insert(scores).values([
    { studentId: byNo.ST20260001.id, examNo: 1, score: "88.50" },
    { studentId: byNo.ST20260001.id, examNo: 2, score: "92.00" },
    { studentId: byNo.ST20260002.id, examNo: 1, score: "79.00" },
    { studentId: byNo.ST20260002.id, examNo: 2, score: "95.00" },
    { studentId: byNo.ST20260003.id, examNo: 1, score: "50.00" },
    { studentId: byNo.ST20260003.id, examNo: 2, score: "40.00" },
    { studentId: byNo.ST20260003.id, examNo: 3, score: "30.00" },
    { studentId: byNo.ST20260004.id, examNo: 1, score: "86.00" },
    { studentId: byNo.ST20260005.id, examNo: 1, score: "61.00" },
    { studentId: byNo.ST20250011.id, examNo: 1, score: "90.00" },
    { studentId: byNo.ST20250012.id, examNo: 1, score: "84.00" },
    { studentId: byNo.ST20250012.id, examNo: 2, score: "88.00" },
  ]);

  await db.insert(pastExperiences).values([
    { studentId: byNo.ST20260001.id, pastSalaryAmount: "9000.00", pastSalaryPeriod: "MONTH", workYears: "2.50", graduationDate: "2022-06-30", intendedCity: "杭州", previousPosition: "Python 开发工程师" },
    { studentId: byNo.ST20260003.id, pastSalaryAmount: "180000.00", pastSalaryPeriod: "YEAR", workYears: "6.00", intendedCity: "上海", previousPosition: "实施工程师" },
    { studentId: byNo.ST20250012.id, pastSalaryAmount: "12000.00", pastSalaryPeriod: "MONTH", workYears: "4.00", intendedCity: "深圳", previousPosition: "数据分析" },
  ]);

  await db.insert(employmentRecords).values([
    { studentId: byNo.ST20260001.id, studentNameSnapshot: "张三", classNoSnapshot: "WL2026-A", employmentOpenDate: "2026-01-10", offerDate: "2026-02-15", companyName: "示例科技有限公司", employmentCity: "杭州", position: "后端开发工程师", salaryAmount: "15000.00", salaryPeriod: "MONTH", pastSalaryAmount: "9000.00", pastSalaryPeriod: "MONTH", previousPosition: "Python 开发工程师", pastGraduationDate: "2022-06-30" },
    { studentId: byNo.ST20260004.id, studentNameSnapshot: "赵敏", classNoSnapshot: "WL2026-B", employmentOpenDate: "2026-05-01", offerDate: "2026-05-21", companyName: "云启数据", employmentCity: "上海", position: "Java 开发工程师", salaryAmount: "220000.00", salaryPeriod: "YEAR" },
    { studentId: byNo.ST20250011.id, studentNameSnapshot: "周杰", classNoSnapshot: "WL2025-C", employmentOpenDate: "2026-01-05", offerDate: "2026-02-10", companyName: "星河测试", employmentCity: "长沙", position: "测试开发工程师", salaryAmount: "14000.00", salaryPeriod: "MONTH" },
    { studentId: byNo.ST20250012.id, studentNameSnapshot: "吴雪", classNoSnapshot: "WL2025-C", employmentOpenDate: "2026-02-01", offerDate: "2026-03-01", companyName: "南方银行科技", employmentCity: "厦门", position: "数据分析师", salaryAmount: "18000.00", salaryPeriod: "MONTH", pastSalaryAmount: "12000.00", pastSalaryPeriod: "MONTH", previousPosition: "数据分析", pastGraduationDate: "2016-06-30" },
  ]);
}
