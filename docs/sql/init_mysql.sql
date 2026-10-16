-- =====================================================================
-- 沃林学生管理系统 · MySQL 8.0 初始化建表脚本（基础版 V1.5）
-- 与 backend/model/*.py 对应；现行 7 张业务表 + users 账号表。
-- 共通规则：BIGINT AUTO_INCREMENT 主键；逻辑删除字段和创建/更新时间字段。
-- 不包含 __table_args__ / 普通索引；业务编号全表唯一的 UNIQUE 约束保留。
-- 仅供新库初始化。已有库请执行 upgrade_mysql_v1_5.sql（先备份）。
-- =====================================================================
CREATE DATABASE IF NOT EXISTS wolin_student DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE wolin_student;

CREATE TABLE classes (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '班级主键ID',
  class_no VARCHAR(30) NOT NULL COMMENT '班级编号，全表唯一',
  class_name VARCHAR(100) NOT NULL COMMENT '班级名称',
  start_date DATE NOT NULL COMMENT '开班日期',
  completion_date DATE NULL COMMENT '班级结课日期，未结课为空',
  class_status VARCHAR(20) NOT NULL DEFAULT '在读' COMMENT '未开班/在读/已结课',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除，1已删除',
  deleted_at DATETIME NULL COMMENT '逻辑删除时间',
  created_at DATETIME NOT NULL COMMENT '创建时间',
  updated_at DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_classes_class_no (class_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='班级表';

CREATE TABLE teachers (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '老师主键ID',
  teacher_no VARCHAR(30) NOT NULL COMMENT '老师编号，全表唯一',
  name VARCHAR(50) NOT NULL COMMENT '老师姓名',
  gender ENUM('男','女','其他') NULL COMMENT '性别',
  specialty VARCHAR(100) NULL COMMENT '教学专长',
  phone VARCHAR(30) NULL COMMENT '电话',
  contact_info VARCHAR(150) NULL COMMENT '微信/邮箱等补充联系方式',
  teaching_years DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '教学年限',
  teacher_status VARCHAR(20) NOT NULL DEFAULT '在职' COMMENT '在职/离职',
  teaching_status VARCHAR(20) NOT NULL DEFAULT '可授课' COMMENT '可授课/暂停授课',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除，1已删除',
  deleted_at DATETIME NULL COMMENT '逻辑删除时间',
  created_at DATETIME NOT NULL COMMENT '创建时间',
  updated_at DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_teachers_teacher_no (teacher_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='老师表';

CREATE TABLE class_teacher_relations (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '关系记录主键ID',
  class_id BIGINT NOT NULL COMMENT '班级ID',
  teacher_id BIGINT NOT NULL COMMENT '老师ID',
  relation_type VARCHAR(30) NOT NULL DEFAULT '授课老师' COMMENT '班主任/授课老师',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除，1已删除',
  deleted_at DATETIME NULL COMMENT '逻辑删除时间',
  created_at DATETIME NOT NULL COMMENT '创建时间',
  updated_at DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  CONSTRAINT fk_ctr_class FOREIGN KEY (class_id) REFERENCES classes (id),
  CONSTRAINT fk_ctr_teacher FOREIGN KEY (teacher_id) REFERENCES teachers (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='班级老师排班关系表';

CREATE TABLE students (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '学生主键ID',
  student_no VARCHAR(30) NOT NULL COMMENT '学生编号，全表唯一',
  class_id BIGINT NOT NULL COMMENT '所属培训班级ID',
  name VARCHAR(50) NOT NULL COMMENT '学生姓名',
  hometown VARCHAR(100) NULL COMMENT '籍贯',
  graduate_school VARCHAR(150) NULL COMMENT '原毕业院校',
  major VARCHAR(100) NULL COMMENT '原专业',
  training_enrollment_date DATE NULL COMMENT '培训机构入学日期',
  training_graduation_date DATE NULL COMMENT '培训机构结课日期',
  education VARCHAR(30) NULL COMMENT '最高学历',
  consultant_no VARCHAR(30) NULL COMMENT '顾问编号（扩展预留）',
  birth_date DATE NOT NULL COMMENT '出生日期，年龄动态计算',
  gender ENUM('男','女','其他') NOT NULL COMMENT '性别',
  avatar_url VARCHAR(500) NULL COMMENT '头像地址（前端预览扩展字段）',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除，1已删除',
  deleted_at DATETIME NULL COMMENT '逻辑删除时间',
  created_at DATETIME NOT NULL COMMENT '创建时间',
  updated_at DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_students_student_no (student_no),
  CONSTRAINT fk_students_class FOREIGN KEY (class_id) REFERENCES classes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生表';

CREATE TABLE scores (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '成绩主键ID',
  student_id BIGINT NOT NULL COMMENT '学生ID',
  exam_no INT NOT NULL COMMENT '考核序次，从1开始',
  score DECIMAL(5,2) NOT NULL COMMENT '成绩0-100',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除，1已删除',
  deleted_at DATETIME NULL COMMENT '逻辑删除时间',
  created_at DATETIME NOT NULL COMMENT '创建时间',
  updated_at DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  CONSTRAINT fk_scores_student FOREIGN KEY (student_id) REFERENCES students (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='考核成绩表';

CREATE TABLE student_past_experiences (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '过往经历主键ID',
  student_id BIGINT NOT NULL COMMENT '学生ID',
  past_salary_amount DECIMAL(12,2) NULL COMMENT '过往薪资金额',
  past_salary_period ENUM('MONTH','YEAR') NULL COMMENT '过往薪资周期',
  work_years DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '工作年限',
  graduation_date DATE NULL COMMENT '原学历毕业日期',
  intended_city VARCHAR(100) NULL COMMENT '意向城市',
  previous_position VARCHAR(100) NULL COMMENT '以往岗位',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除，1已删除',
  deleted_at DATETIME NULL COMMENT '逻辑删除时间',
  created_at DATETIME NOT NULL COMMENT '创建时间',
  updated_at DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  CONSTRAINT fk_past_experiences_student FOREIGN KEY (student_id) REFERENCES students (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生过往经历表';

CREATE TABLE employment_records (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '就业记录主键ID',
  student_id BIGINT NOT NULL COMMENT '学生ID，多条记录保留多段Offer历史',
  student_name_snapshot VARCHAR(50) NOT NULL COMMENT '学生姓名快照',
  class_no_snapshot VARCHAR(30) NOT NULL COMMENT '班级编号快照，服务端新增时填入',
  employment_open_date DATE NULL COMMENT '就业开放日期，必须不早于学生结课日期',
  offer_date DATE NULL COMMENT 'Offer日期，必须不早于就业开放日期',
  company_name VARCHAR(150) NOT NULL COMMENT '就业公司名称',
  employment_city VARCHAR(100) NULL COMMENT '就业城市',
  position VARCHAR(100) NULL COMMENT '就业岗位',
  salary_amount DECIMAL(12,2) NOT NULL COMMENT '原始薪资金额',
  salary_period ENUM('MONTH','YEAR') NOT NULL COMMENT '薪资周期',
  offer_status VARCHAR(20) NOT NULL DEFAULT '待处理' COMMENT '待处理/已接受/已拒绝；学生多个Offer可分别记录',
  past_salary_amount DECIMAL(12,2) NULL COMMENT '就业前薪资快照',
  past_salary_period ENUM('MONTH','YEAR') NULL COMMENT '就业前薪资周期快照',
  previous_position VARCHAR(100) NULL COMMENT '就业前岗位快照',
  past_graduation_date DATE NULL COMMENT '原学历毕业日期快照',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除，1已删除',
  deleted_at DATETIME NULL COMMENT '逻辑删除时间',
  created_at DATETIME NOT NULL COMMENT '创建时间',
  updated_at DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  CONSTRAINT fk_employment_records_student FOREIGN KEY (student_id) REFERENCES students (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='就业记录与Offer表';

CREATE TABLE users (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户主键ID',
  username VARCHAR(50) NOT NULL COMMENT '登录账号，全表唯一',
  password_hash VARCHAR(255) NOT NULL COMMENT 'bcrypt密码哈希，禁止存明文',
  display_name VARCHAR(50) NOT NULL COMMENT '显示名称',
  role VARCHAR(20) NOT NULL DEFAULT 'viewer' COMMENT 'admin/head_teacher/teacher/employment/viewer',
  class_id BIGINT NULL COMMENT '班主任/授课老师所属班级；其他角色为空',
  token VARCHAR(64) NULL COMMENT '登录令牌，退出时清空',
  is_active TINYINT NOT NULL DEFAULT 1 COMMENT '账号启用状态：1启用，0停用',
  is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除，1已删除',
  deleted_at DATETIME NULL COMMENT '逻辑删除时间',
  created_at DATETIME NOT NULL COMMENT '创建时间',
  updated_at DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_username (username),
  CONSTRAINT fk_users_class FOREIGN KEY (class_id) REFERENCES classes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='登录用户与角色表';
