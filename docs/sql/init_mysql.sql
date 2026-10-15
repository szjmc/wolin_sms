-- =====================================================================
-- 沃林学生管理系统 · MySQL 8.0 初始化建表脚本（基础版 V1.3，2026-10 修订）
-- 本脚本与 backend/model 中的 SQLAlchemy 模型保持一致。
-- 说明：
--   1. 所有表主键 id 均为 BIGINT AUTO_INCREMENT
--   2. 所有表都有 is_deleted / deleted_at / created_at / updated_at 公共字段
--   3. 业务编号保留 UNIQUE 防重；高频历史查询按模块需要建立“关联 ID + 逻辑删除”组合索引
--   4. 后端启动时 Base.metadata.create_all() 也会自动建表，本脚本供 DBA 审核或手动初始化使用
--   5. 请勿在生产库直接执行 DROP/重建；升级已有数据库请编写 ALTER 脚本并先备份
-- =====================================================================
CREATE DATABASE IF NOT EXISTS wolin_student DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE wolin_student;

CREATE TABLE classes (
	id BIGINT NOT NULL COMMENT '班级主键ID' AUTO_INCREMENT,
	class_no VARCHAR(30) NOT NULL COMMENT '班级编号，如 WL2026-A',
	class_name VARCHAR(100) NOT NULL COMMENT '班级名称',
	start_date DATE NOT NULL COMMENT '开班日期',
	completion_date DATE COMMENT '班级结课日期，未结课为空',
	class_status VARCHAR(20) NOT NULL COMMENT '班级状态：未开班/在读/已结课',
	is_deleted TINYINT NOT NULL COMMENT '逻辑删除：0=未删除，1=已删除' DEFAULT '0',
	deleted_at DATETIME COMMENT '逻辑删除时间',
	created_at DATETIME NOT NULL COMMENT '创建时间',
	updated_at DATETIME NOT NULL COMMENT '更新时间',
	PRIMARY KEY (id),
	UNIQUE (class_no)
)ENGINE=InnoDB COMMENT='班级表' CHARSET=utf8mb4;

CREATE TABLE teachers (
	id BIGINT NOT NULL COMMENT '老师主键ID' AUTO_INCREMENT,
	teacher_no VARCHAR(30) NOT NULL COMMENT '老师编号',
	name VARCHAR(50) NOT NULL COMMENT '老师姓名',
	gender ENUM('男','女','其他') COMMENT '性别：男/女/其他',
	specialty VARCHAR(100) COMMENT '教学专长',
	phone VARCHAR(30) COMMENT '手机号（只保存电话）',
	contact_info VARCHAR(150) COMMENT '补充联系方式，如微信、邮箱',
	teaching_years NUMERIC(5, 2) NOT NULL COMMENT '教学年限，可为小数' DEFAULT '0',
	teacher_status VARCHAR(20) NOT NULL COMMENT '老师状态：在职/离职',
	-- [修改说明] 原代码：老师表只有任职状态；修改原因：排班需独立维护可授课/暂停授课；修改为：新增默认“可授课”的 teaching_status，和 backend-bak ORM 保持一致。
	teaching_status VARCHAR(20) NOT NULL COMMENT '授课状态：可授课/暂停授课' DEFAULT '可授课',
	is_deleted TINYINT NOT NULL COMMENT '逻辑删除：0=未删除，1=已删除' DEFAULT '0',
	deleted_at DATETIME COMMENT '逻辑删除时间',
	created_at DATETIME NOT NULL COMMENT '创建时间',
	updated_at DATETIME NOT NULL COMMENT '更新时间',
	PRIMARY KEY (id),
	UNIQUE (teacher_no)
)ENGINE=InnoDB COMMENT='老师表' CHARSET=utf8mb4;

CREATE TABLE class_teacher_relations (
	id BIGINT NOT NULL COMMENT '关系记录主键ID' AUTO_INCREMENT,
	class_id BIGINT NOT NULL COMMENT '班级ID',
	teacher_id BIGINT NOT NULL COMMENT '老师ID',
	relation_type VARCHAR(30) NOT NULL COMMENT '关系类型：班主任/授课老师',
	is_deleted TINYINT NOT NULL COMMENT '逻辑删除：0=未删除，1=已删除' DEFAULT '0',
	deleted_at DATETIME COMMENT '逻辑删除时间',
	created_at DATETIME NOT NULL COMMENT '创建时间',
	updated_at DATETIME NOT NULL COMMENT '更新时间',
	PRIMARY KEY (id),
	FOREIGN KEY(class_id) REFERENCES classes (id),
	FOREIGN KEY(teacher_id) REFERENCES teachers (id)
)ENGINE=InnoDB COMMENT='班级老师关系表' CHARSET=utf8mb4;

CREATE TABLE students (
	id BIGINT NOT NULL COMMENT '学生主键ID' AUTO_INCREMENT,
	student_no VARCHAR(30) NOT NULL COMMENT '学生编号',
	class_id BIGINT NOT NULL COMMENT '所属培训班级ID',
	name VARCHAR(50) NOT NULL COMMENT '学生姓名',
	hometown VARCHAR(100) COMMENT '籍贯',
	graduate_school VARCHAR(150) COMMENT '原毕业院校',
	major VARCHAR(100) COMMENT '原专业',
	training_enrollment_date DATE COMMENT '培训入学日期（培训机构）',
	training_graduation_date DATE COMMENT '培训毕业/结课日期（培训机构）',
	education VARCHAR(30) COMMENT '学历',
	consultant_no VARCHAR(30) COMMENT '顾问编号（扩展预留，不建外键）',
	birth_date DATE NOT NULL COMMENT '出生日期（年龄由此动态计算）',
	gender ENUM('男','女','其他') NOT NULL COMMENT '性别：男/女/其他',
	is_deleted TINYINT NOT NULL COMMENT '逻辑删除：0=未删除，1=已删除' DEFAULT '0',
	deleted_at DATETIME COMMENT '逻辑删除时间',
	created_at DATETIME NOT NULL COMMENT '创建时间',
	updated_at DATETIME NOT NULL COMMENT '更新时间',
	PRIMARY KEY (id),
	UNIQUE (student_no),
	FOREIGN KEY(class_id) REFERENCES classes (id)
)ENGINE=InnoDB COMMENT='学生表' CHARSET=utf8mb4;

CREATE TABLE employment_records (
	id BIGINT NOT NULL COMMENT '就业记录主键ID' AUTO_INCREMENT,
	student_id BIGINT NOT NULL COMMENT '学生ID',
	student_name_snapshot VARCHAR(50) NOT NULL COMMENT '学生姓名快照',
	class_no_snapshot VARCHAR(30) NOT NULL COMMENT '班级编号快照（必填，新增时服务端填入）',
	employment_open_date DATE COMMENT '就业开放日期',
	offer_date DATE COMMENT 'Offer 日期',
	company_name VARCHAR(150) NOT NULL COMMENT '就业公司名称',
	employment_city VARCHAR(100) COMMENT '就业城市',
	position VARCHAR(100) COMMENT '就业岗位',
	salary_amount NUMERIC(12, 2) NOT NULL COMMENT '薪资金额（原始值）',
	salary_period ENUM('MONTH','YEAR') NOT NULL COMMENT '薪资周期：MONTH=月薪，YEAR=年薪',
	-- [修改说明] 原代码：就业表未保存就业前经历；修改原因：若每次联查学生当前档案，历史薪资对比会随档案修改；修改为：保存创建就业记录时的薪资、岗位和原学历毕业日期快照。
	past_salary_amount NUMERIC(12, 2) COMMENT '创建就业记录时的过往薪资金额快照',
	past_salary_period ENUM('MONTH','YEAR') COMMENT '过往薪资周期快照：MONTH/YEAR',
	previous_position VARCHAR(100) COMMENT '创建就业记录时的以往岗位快照',
	past_graduation_date DATE COMMENT '创建就业记录时的原学历毕业日期快照',
	is_deleted TINYINT NOT NULL COMMENT '逻辑删除：0=未删除，1=已删除' DEFAULT '0',
	deleted_at DATETIME COMMENT '逻辑删除时间',
	created_at DATETIME NOT NULL COMMENT '创建时间',
	updated_at DATETIME NOT NULL COMMENT '更新时间',
	PRIMARY KEY (id),
	FOREIGN KEY(student_id) REFERENCES students (id),
	KEY idx_emp_student_deleted (student_id, is_deleted)
)ENGINE=InnoDB COMMENT='就业记录表' CHARSET=utf8mb4;

CREATE TABLE scores (
	id BIGINT NOT NULL COMMENT '成绩主键ID' AUTO_INCREMENT,
	student_id BIGINT NOT NULL COMMENT '学生ID',
	exam_no INTEGER NOT NULL COMMENT '考核序次，从 1 开始',
	score NUMERIC(5, 2) NOT NULL COMMENT '成绩，0~100',
	is_deleted TINYINT NOT NULL COMMENT '逻辑删除：0=未删除，1=已删除' DEFAULT '0',
	deleted_at DATETIME COMMENT '逻辑删除时间',
	created_at DATETIME NOT NULL COMMENT '创建时间',
	updated_at DATETIME NOT NULL COMMENT '更新时间',
	PRIMARY KEY (id),
	FOREIGN KEY(student_id) REFERENCES students (id)
)ENGINE=InnoDB COMMENT='考核成绩表' CHARSET=utf8mb4;

CREATE TABLE student_past_experiences (
	id BIGINT NOT NULL COMMENT '过往经历主键ID' AUTO_INCREMENT,
	student_id BIGINT NOT NULL COMMENT '学生ID',
	past_salary_amount NUMERIC(12, 2) COMMENT '过往薪资金额',
	past_salary_period ENUM('MONTH','YEAR') COMMENT '过往薪资周期：MONTH=月薪，YEAR=年薪',
	work_years NUMERIC(5, 2) NOT NULL COMMENT '工作年限' DEFAULT '0',
	graduation_date DATE COMMENT '过往学历毕业日期',
	intended_city VARCHAR(100) COMMENT '就业意向城市',
	previous_position VARCHAR(100) COMMENT '以往岗位',
	is_deleted TINYINT NOT NULL COMMENT '逻辑删除：0=未删除，1=已删除' DEFAULT '0',
	deleted_at DATETIME COMMENT '逻辑删除时间',
	created_at DATETIME NOT NULL COMMENT '创建时间',
	updated_at DATETIME NOT NULL COMMENT '更新时间',
	PRIMARY KEY (id),
	FOREIGN KEY(student_id) REFERENCES students (id)
)ENGINE=InnoDB COMMENT='学生过往经历表' CHARSET=utf8mb4;
