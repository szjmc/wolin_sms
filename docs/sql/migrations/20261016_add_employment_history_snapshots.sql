-- 就业记录模块：为已有 MySQL employment_records 表补充不可变的就业前经历快照。
-- 执行前请确认目标库已完成备份；新建数据库直接使用 docs/sql/init_mysql.sql 即可。
-- 四列均可空，因此已有就业记录不会被错误回填为学生当前档案。
ALTER TABLE employment_records
    ADD COLUMN past_salary_amount NUMERIC(12, 2) NULL
        COMMENT '创建就业记录时的过往薪资金额快照'
        AFTER salary_period,
    ADD COLUMN past_salary_period ENUM('MONTH','YEAR') NULL
        COMMENT '过往薪资周期快照：MONTH/YEAR'
        AFTER past_salary_amount,
    ADD COLUMN previous_position VARCHAR(100) NULL
        COMMENT '创建就业记录时的以往岗位快照'
        AFTER past_salary_period,
    ADD COLUMN past_graduation_date DATE NULL
        COMMENT '创建就业记录时的原学历毕业日期快照'
        AFTER previous_position,
    ADD INDEX idx_emp_student_deleted (student_id, is_deleted);
