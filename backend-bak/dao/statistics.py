"""统计分析数据访问层。

所有统计在 SQL 查询边界排除逻辑删除数据。成绩和就业记录除过滤自身外，还必须
联接并过滤所属学生；班级学情还要过滤有效班级。
"""
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from dao.stu_records_dao import annualized_salary_expression
from model.class_info import ClassInfo
from model.score import Score
from model.stu_records_model import EmploymentRecord
from model.students_model import StudentDB
from model.teacher import Teacher


# [修改说明] 原代码：DAO 导入 model.students/model.classes 等不存在模块，并混入 Depends、HTTPException、响应字典和 MySQL 专属函数；修改原因：模块无法导入，SQLite 无法执行且各统计遗漏逻辑删除条件；修改为：保留 dao/statistics.py 文件，改用现有正式 ORM，只返回查询结果，业务响应统一由 API 层组装。
def get_system_overview_counts(db: Session) -> dict[str, int]:
    """首页四项有效记录总量；就业记录同时受所属学生可见性约束。"""
    student_total = db.query(func.count(StudentDB.id)).filter(
        StudentDB.is_deleted == 0
    ).scalar()
    class_total = db.query(func.count(ClassInfo.id)).filter(
        ClassInfo.is_deleted == 0
    ).scalar()
    teacher_total = db.query(func.count(Teacher.id)).filter(
        Teacher.is_deleted == 0
    ).scalar()
    employment_total = (
        db.query(func.count(EmploymentRecord.id))
        .join(StudentDB, StudentDB.id == EmploymentRecord.student_id)
        .filter(
            EmploymentRecord.is_deleted == 0,
            StudentDB.is_deleted == 0,
        )
        .scalar()
    )
    return {
        "student_total": int(student_total or 0),
        "class_total": int(class_total or 0),
        "teacher_total": int(teacher_total or 0),
        "employment_total": int(employment_total or 0),
    }


def count_students_group_by_class_and_gender(
    db: Session,
    class_id: int | None = None,
):
    """按班级和性别统计未删除学生。"""
    query = db.query(
        StudentDB.class_id,
        StudentDB.gender,
        func.count(StudentDB.id).label("student_count"),
    ).filter(StudentDB.is_deleted == 0)
    if class_id is not None:
        query = query.filter(StudentDB.class_id == class_id)
    return (
        query.group_by(StudentDB.class_id, StudentDB.gender)
        .order_by(StudentDB.class_id.asc(), StudentDB.gender.asc())
        .all()
    )


# [修改说明] 原代码：全达标查询使用 MIN(score) > 80，且没有过滤已删除成绩；修改原因：80 分应计入达标，逻辑删除低分不应继续影响结果；修改为：有效成绩按学生分组并使用 HAVING MIN(score) >= 参数，天然排除没有成绩的学生。
def list_student_ids_all_scores_at_least(db: Session, min_score):
    rows = (
        db.query(Score.student_id)
        .join(StudentDB, StudentDB.id == Score.student_id)
        .filter(Score.is_deleted == 0, StudentDB.is_deleted == 0)
        .group_by(Score.student_id)
        .having(func.min(Score.score) >= min_score)
        .order_by(Score.student_id.asc())
        .all()
    )
    return [row.student_id for row in rows]


def list_failure_counts(db: Session, fail_score, min_fail_count: int):
    """返回不及格次数达到阈值的学生，按次数降序、学生 ID 升序。"""
    fail_count = func.count(Score.id)
    return (
        db.query(Score.student_id, fail_count.label("fail_count"))
        .join(StudentDB, StudentDB.id == Score.student_id)
        .filter(
            Score.is_deleted == 0,
            StudentDB.is_deleted == 0,
            Score.score < fail_score,
        )
        .group_by(Score.student_id)
        .having(fail_count >= min_fail_count)
        .order_by(fail_count.desc(), Score.student_id.asc())
        .all()
    )


def list_class_exam_averages(
    db: Session,
    exam_no: int | None = None,
    class_id: int | None = None,
):
    """按考核序次和班级统计平均分及有效成绩样本量。"""
    query = (
        db.query(
            ClassInfo.id.label("class_id"),
            ClassInfo.class_no,
            ClassInfo.class_name,
            Score.exam_no,
            func.avg(Score.score).label("average_score"),
            func.count(Score.id).label("sample_count"),
        )
        .select_from(Score)
        .join(StudentDB, StudentDB.id == Score.student_id)
        .join(ClassInfo, ClassInfo.id == StudentDB.class_id)
        .filter(
            Score.is_deleted == 0,
            StudentDB.is_deleted == 0,
            ClassInfo.is_deleted == 0,
        )
    )
    if exam_no is not None:
        query = query.filter(Score.exam_no == exam_no)
    if class_id is not None:
        query = query.filter(ClassInfo.id == class_id)
    return (
        query.group_by(
            ClassInfo.id,
            ClassInfo.class_no,
            ClassInfo.class_name,
            Score.exam_no,
        )
        .order_by(Score.exam_no.asc(), ClassInfo.id.asc())
        .all()
    )


# [修改说明] 原代码：薪资排序把小写 year 当成年薪，其余全部乘 12，并且未排除已删除记录和学生；修改原因：YEAR 会被错误放大十二倍，删除数据仍进入榜单；修改为：复用就业 DAO 的 MONTH×12/YEAR 原值表达式，并显式联表过滤可见性。
def list_top_salary_records(db: Session, limit: int):
    annualized_salary = annualized_salary_expression()
    return (
        db.query(EmploymentRecord)
        .join(StudentDB, StudentDB.id == EmploymentRecord.student_id)
        .filter(
            EmploymentRecord.is_deleted == 0,
            StudentDB.is_deleted == 0,
        )
        .order_by(annualized_salary.desc(), EmploymentRecord.id.asc())
        .limit(limit)
        .all()
    )


# [修改说明] 原代码：就业时长使用 MySQL DATEDIFF，单条和班级平均查询还会保留日期不完整或已删除记录；修改原因：跨数据库不可执行且统计口径失真；修改为：DAO 只取两个日期齐全的可见记录，API 使用 Python date 相减计算自然日。
def list_records_with_both_dates(
    db: Session,
    student_id: int | None = None,
    class_no_snapshot: str | None = None,
):
    query = (
        db.query(EmploymentRecord)
        .join(StudentDB, StudentDB.id == EmploymentRecord.student_id)
        .filter(
            EmploymentRecord.is_deleted == 0,
            StudentDB.is_deleted == 0,
            EmploymentRecord.employment_open_date.is_not(None),
            EmploymentRecord.offer_date.is_not(None),
        )
    )
    if student_id is not None:
        query = query.filter(EmploymentRecord.student_id == student_id)
    if class_no_snapshot is not None:
        query = query.filter(
            EmploymentRecord.class_no_snapshot == class_no_snapshot
        )
    return query.order_by(
        EmploymentRecord.class_no_snapshot.asc(), EmploymentRecord.id.asc()
    ).all()


def get_class_score_summary(db: Session, class_id: int):
    """班级详情页的成绩条数、覆盖人数、及格条数和平均分。"""
    return (
        db.query(
            func.count(Score.id).label("total_scores"),
            func.count(func.distinct(Score.student_id)).label("graded_students"),
            func.coalesce(
                func.sum(case((Score.score >= 60, 1), else_=0)),
                0,
            ).label("passing_scores"),
            func.avg(Score.score).label("average_score"),
        )
        .select_from(Score)
        .join(StudentDB, StudentDB.id == Score.student_id)
        .filter(
            Score.is_deleted == 0,
            StudentDB.is_deleted == 0,
            StudentDB.class_id == class_id,
        )
        .one()
    )


def count_class_qualified_students(
    db: Session,
    class_id: int,
    min_score=80,
) -> int:
    """班级中至少有一条成绩且全部有效成绩达标的学生数。"""
    qualified = (
        db.query(Score.student_id.label("student_id"))
        .join(StudentDB, StudentDB.id == Score.student_id)
        .filter(
            Score.is_deleted == 0,
            StudentDB.is_deleted == 0,
            StudentDB.class_id == class_id,
        )
        .group_by(Score.student_id)
        .having(func.min(Score.score) >= min_score)
        .subquery()
    )
    return int(db.query(func.count()).select_from(qualified).scalar() or 0)


def count_employed_students_by_class_snapshot(
    db: Session,
    class_no_snapshot: str,
) -> int:
    """按就业记录历史班号快照去重统计仍可见的已就业学生。"""
    count_value = (
        db.query(func.count(func.distinct(EmploymentRecord.student_id)))
        .join(StudentDB, StudentDB.id == EmploymentRecord.student_id)
        .filter(
            EmploymentRecord.is_deleted == 0,
            StudentDB.is_deleted == 0,
            EmploymentRecord.class_no_snapshot == class_no_snapshot,
        )
        .scalar()
    )
    return int(count_value or 0)
