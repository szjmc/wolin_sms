"""
统计分析数据访问层
==================
每个函数只执行一条查询，把"过滤 + 分组统计"交给数据库完成。

统一规则：所有统计查询都必须在 SQL 里排除逻辑删除的数据：
- 学生：Student.is_deleted == 0
- 成绩 / 就业记录：自身 is_deleted == 0，并且所属学生 is_deleted == 0
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from dao.employment_record_dao import annualized_salary_expression
from model.class_info import ClassInfo
from model.employment_record import EmploymentRecord
from model.score import Score
from model.student import Student


def count_students_group_by_class_and_gender(db: Session):
    """
    按"班级 + 性别"分组，统计未删除学生的人数。
    返回的每一行有 3 个字段：class_id（班级ID）、gender（性别）、student_count（人数）
    """
    return (
        db.query(
            Student.class_id,
            Student.gender,
            func.count(Student.id).label("student_count"),
        )
        .filter(Student.is_deleted == 0)
        .group_by(Student.class_id, Student.gender)
        .all()
    )


def list_student_ids_all_scores_at_least(db: Session, min_score):
    """
    查询"所有有效成绩都 >= min_score"的学生ID列表。

    思路：按学生分组，取每个学生的最低分；最低分 >= min_score，说明所有成绩都达标。
    没有任何有效成绩的学生不会出现在分组结果里，所以会被自动排除（没有成绩不算达标）。
    """
    rows = (
        db.query(Score.student_id)
        .join(Student, Student.id == Score.student_id)
        .filter(Score.is_deleted == 0, Student.is_deleted == 0)
        .group_by(Score.student_id)
        .having(func.min(Score.score) >= min_score)
        .all()
    )
    student_ids = []
    for row in rows:
        student_ids.append(row.student_id)
    return student_ids


def list_failure_counts(db: Session, fail_score, min_fail_count: int):
    """
    统计每个学生"低于不及格线"的有效成绩条数，只返回条数 >= min_fail_count 的学生。
    返回的每一行有 2 个字段：student_id、fail_count，按不及格次数从多到少排序。
    """
    fail_count = func.count(Score.id)
    return (
        db.query(Score.student_id, fail_count.label("fail_count"))
        .join(Student, Student.id == Score.student_id)
        .filter(
            Score.is_deleted == 0,
            Student.is_deleted == 0,
            Score.score < fail_score,
        )
        .group_by(Score.student_id)
        .having(fail_count >= min_fail_count)
        .order_by(fail_count.desc(), Score.student_id.asc())
        .all()
    )


def list_class_exam_averages(db: Session, exam_no: int | None = None, class_id: int | None = None):
    """
    按"考核序次 + 班级"分组计算平均分，同时统计每组的有效成绩条数（样本量）。
    只统计：未删除的成绩 + 未删除的学生 + 未删除的班级。
    返回的每一行有 6 个字段：class_id、class_no、class_name、exam_no、average_score、sample_count
    """
    query = (
        db.query(
            ClassInfo.id.label("class_id"),
            ClassInfo.class_no,
            ClassInfo.class_name,
            Score.exam_no,
            func.avg(Score.score).label("average_score"),
            func.count(Score.id).label("sample_count"),
        )
        # 从成绩表出发 → 关联学生表 → 再关联班级表
        .select_from(Score)
        .join(Student, Student.id == Score.student_id)
        .join(ClassInfo, ClassInfo.id == Student.class_id)
        .filter(
            Score.is_deleted == 0,
            Student.is_deleted == 0,
            ClassInfo.is_deleted == 0,
        )
    )
    if exam_no is not None:
        query = query.filter(Score.exam_no == exam_no)
    if class_id is not None:
        query = query.filter(ClassInfo.id == class_id)

    return (
        query.group_by(ClassInfo.id, ClassInfo.class_no, ClassInfo.class_name, Score.exam_no)
        .order_by(Score.exam_no.asc(), ClassInfo.id.asc())
        .all()
    )


def list_top_salary_records(db: Session, limit: int):
    """
    按"年薪等价值"从高到低查询有效就业记录，取前 limit 条。
    年薪等价值相同时，按记录ID从小到大排（先录入的排前面）。
    """
    annualized_salary = annualized_salary_expression()
    return (
        db.query(EmploymentRecord)
        .join(Student, Student.id == EmploymentRecord.student_id)
        .filter(EmploymentRecord.is_deleted == 0, Student.is_deleted == 0)
        .order_by(annualized_salary.desc(), EmploymentRecord.id.asc())
        .limit(limit)
        .all()
    )


def list_records_with_both_dates(
    db: Session,
    student_id: int | None = None,
    class_no_snapshot: str | None = None,
):
    """
    查询"就业开放日期"和"Offer 日期"都有值的有效就业记录（用于计算就业时长）。
    缺少任何一个日期的记录无法计算时长，不参与统计。
    """
    query = (
        db.query(EmploymentRecord)
        .join(Student, Student.id == EmploymentRecord.student_id)
        .filter(
            EmploymentRecord.is_deleted == 0,
            Student.is_deleted == 0,
            EmploymentRecord.employment_open_date.is_not(None),
            EmploymentRecord.offer_date.is_not(None),
        )
    )
    if student_id is not None:
        query = query.filter(EmploymentRecord.student_id == student_id)
    if class_no_snapshot is not None:
        query = query.filter(EmploymentRecord.class_no_snapshot == class_no_snapshot)

    return query.order_by(EmploymentRecord.class_no_snapshot.asc(), EmploymentRecord.id.asc()).all()
