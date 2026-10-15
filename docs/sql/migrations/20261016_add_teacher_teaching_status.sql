-- 班级老师排班模块：为已有 MySQL teachers 表补充独立授课状态。
-- 执行前请确认目标库已完成备份；新建数据库直接使用 docs/sql/init_mysql.sql 即可。
ALTER TABLE teachers
    ADD COLUMN teaching_status VARCHAR(20) NOT NULL DEFAULT '可授课'
    COMMENT '授课状态：可授课/暂停授课'
    AFTER teacher_status;
