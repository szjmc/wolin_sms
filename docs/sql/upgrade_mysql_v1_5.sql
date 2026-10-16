-- =====================================================================
-- 沃林学生管理系统 · MySQL 8.0 已有库升级脚本 → V1.5
-- 执行前先备份！本脚本不是“每次启动运行”的脚本，只在旧库升级时执行一次。
-- 不 DROP、不重建业务表，不删除历史就业/账号/排班数据。
-- 执行方式：mysql -uroot -p wolin_student < docs/sql/upgrade_mysql_v1_5.sql
-- =====================================================================
USE wolin_student;

-- 1) 老师增加授课状态。历史老师默认可授课，之后由管理员按实际情况调整。
ALTER TABLE teachers
  ADD COLUMN teaching_status VARCHAR(20) NOT NULL DEFAULT '可授课'
  COMMENT '授课状态：可授课/暂停授课' AFTER teacher_status;

-- 2) 就业记录增加 Offer 状态。历史记录默认待处理，不会擅自替用户决定 Offer 是否接受。
ALTER TABLE employment_records
  ADD COLUMN offer_status VARCHAR(20) NOT NULL DEFAULT '待处理'
  COMMENT '待处理/已接受/已拒绝' AFTER salary_period;

-- 3) 老数据可能没有班级快照：先用学生当前班级补齐；
--    若学生或班级历史已不可关联，明确填入“历史班级未记录”，保证字段不为空且不伪造班号。
UPDATE employment_records e
LEFT JOIN students s ON s.id = e.student_id
LEFT JOIN classes c ON c.id = s.class_id
SET e.class_no_snapshot = COALESCE(c.class_no, '历史班级未记录')
WHERE e.class_no_snapshot IS NULL OR TRIM(e.class_no_snapshot) = '';
ALTER TABLE employment_records
  MODIFY COLUMN class_no_snapshot VARCHAR(30) NOT NULL
  COMMENT '班级编号快照（必填）';

-- 4) 新增用户、角色与登录令牌表。password_hash 必须是 bcrypt 哈希，禁止存明文密码。
CREATE TABLE IF NOT EXISTS users (
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
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_username (username),
  CONSTRAINT fk_users_class FOREIGN KEY (class_id) REFERENCES classes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='登录用户与角色表';

-- 5) 排班规则上线前的人工核查：
--    规则是一位老师同时只能负责一个未结课班级；班主任与授课老师必须不同人。
--    此脚本不自动删除任何旧排班，避免静默丢历史；请先人工查重复：
--
-- SELECT r.teacher_id, t.name, COUNT(DISTINCT r.class_id) AS active_class_count
-- FROM class_teacher_relations r
-- JOIN classes c ON c.id = r.class_id
-- JOIN teachers t ON t.id = r.teacher_id
-- WHERE r.is_deleted = 0 AND c.is_deleted = 0 AND c.status <> 3
-- GROUP BY r.teacher_id, t.name
-- HAVING COUNT(DISTINCT r.class_id) > 1;
--
-- 对查到的冲突，由业务负责人确认保留哪条关系后，再把多余关系设 is_deleted=1。
-- =====================================================================
