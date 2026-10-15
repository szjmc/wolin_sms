"""成绩数据访问层：负责 scores 表及成绩大表的数据库查询。"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, case, false, func, or_
from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from model.class_info import ClassInfo
from model.score import Score
from model.students_model import StudentDB


# [修改说明] 原代码：DAO 只有 ScoreDAO 类且分页、全员联表、汇总和批量写入均缺失；修改原因：核心列表无法返回统一分页，前端成绩大表及 Excel 导入导出也没有可复用查询边界；修改为：保留 ScoreDAO 兼容外观，同时补齐函数式核心 CRUD、联表筛选、汇总、序次选项与原子批量写入。
def get_score_by_id(db: Session, score_id: int):
    return (
        db.query(Score)
        .filter(Score.id == score_id, Score.is_deleted == 0)
        .first()
    )


def get_active_score_by_exam(db: Session, student_id: int, exam_no: int):
    """按业务定位键查询一条有效成绩。"""
    return (
        db.query(Score)
        .filter(
            Score.student_id == student_id,
            Score.exam_no == exam_no,
            Score.is_deleted == 0,
        )
        .first()
    )


def list_scores_by_student(
    db: Session,
    student_id: int,
    page: int,
    page_size: int,
    exam_no: int | None = None,
):
    query = db.query(Score).filter(
        Score.student_id == student_id, Score.is_deleted == 0
    )
    if exam_no is not None:
        query = query.filter(Score.exam_no == exam_no)
    query = query.order_by(Score.exam_no.asc(), Score.id.asc())
    return paginate(query, page, page_size)


def create_score(db: Session, data: dict):
    score = Score(**data)
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def create_score_guarded(db: Session, data: dict):
    """锁定学生后复查并新增；返回 (成绩, 冲突原因)。"""
    try:
        student = (
            db.query(StudentDB)
            .filter(
                StudentDB.id == data["student_id"],
                StudentDB.is_deleted == 0,
            )
            .with_for_update()
            .first()
        )
        if student is None:
            db.rollback()
            return None, "student"
        if (
            get_active_score_by_exam(
                db, data["student_id"], data["exam_no"]
            )
            is not None
        ):
            db.rollback()
            return None, "duplicate"
        score = Score(**data)
        db.add(score)
        db.commit()
        db.refresh(score)
        return score, None
    except Exception:
        db.rollback()
        raise


def update_score(db: Session, score: Score, changes: dict):
    for field_name, value in changes.items():
        setattr(score, field_name, value)
    db.commit()
    db.refresh(score)
    return score


def delete_score(db: Session, score: Score):
    score.is_deleted = 1
    score.deleted_at = datetime.now()
    db.commit()


def _overview_query(
    db: Session,
    q: str | None = None,
    class_id: int | None = None,
    student_id: int | None = None,
    exam_no: int | None = None,
    min_score: Decimal | None = None,
    max_score: Decimal | None = None,
    score_band: str | None = None,
    keys: list[tuple[int, int]] | None = None,
):
    """构造全员成绩可见性及筛选查询。"""
    query = (
        db.query(Score, StudentDB, ClassInfo)
        .join(StudentDB, StudentDB.id == Score.student_id)
        .join(ClassInfo, ClassInfo.id == StudentDB.class_id)
        .filter(
            Score.is_deleted == 0,
            StudentDB.is_deleted == 0,
            ClassInfo.is_deleted == 0,
        )
    )

    q = clean_text(q)
    if q is not None:
        keyword = f"%{q}%"
        query = query.filter(
            or_(StudentDB.name.like(keyword), StudentDB.student_no.like(keyword))
        )
    if class_id is not None:
        query = query.filter(StudentDB.class_id == class_id)
    if student_id is not None:
        query = query.filter(StudentDB.id == student_id)
    if exam_no is not None:
        query = query.filter(Score.exam_no == exam_no)
    if min_score is not None:
        query = query.filter(Score.score >= min_score)
    if max_score is not None:
        query = query.filter(Score.score <= max_score)
    if score_band == "excellent":
        query = query.filter(Score.score >= 80)
    elif score_band == "pass":
        query = query.filter(Score.score >= 60, Score.score < 80)
    elif score_band == "fail":
        query = query.filter(Score.score < 60)

    if keys is not None:
        if not keys:
            query = query.filter(false())
        else:
            query = query.filter(
                or_(
                    *[
                        and_(
                            Score.student_id == selected_student_id,
                            Score.exam_no == selected_exam_no,
                        )
                        for selected_student_id, selected_exam_no in keys
                    ]
                )
            )
    return query


def _order_overview(query, sort: str):
    if sort == "score_desc":
        return query.order_by(Score.score.desc(), Score.id.desc())
    if sort == "score_asc":
        return query.order_by(Score.score.asc(), Score.id.desc())
    if sort == "exam_asc":
        return query.order_by(Score.exam_no.asc(), Score.id.desc())
    return query.order_by(Score.updated_at.desc(), Score.id.desc())


def list_score_overviews(
    db: Session,
    page: int,
    page_size: int,
    sort: str = "latest",
    **filters,
):
    query = _order_overview(_overview_query(db, **filters), sort)
    return paginate(query, page, page_size)


def list_score_overviews_for_export(
    db: Session,
    limit: int,
    sort: str = "latest",
    **filters,
):
    query = _order_overview(_overview_query(db, **filters), sort)
    return query.limit(limit).all()


def summarize_scores(db: Session, **filters):
    query = _overview_query(db, **filters).order_by(None)
    return query.with_entities(
        func.count(Score.id),
        func.avg(Score.score),
        func.coalesce(
            func.sum(case((Score.score >= 60, 1), else_=0)),
            0,
        ),
        func.coalesce(
            func.sum(case((Score.score >= 80, 1), else_=0)),
            0,
        ),
    ).one()


def list_exam_numbers(db: Session) -> list[int]:
    rows = (
        db.query(Score.exam_no)
        .join(StudentDB, StudentDB.id == Score.student_id)
        .join(ClassInfo, ClassInfo.id == StudentDB.class_id)
        .filter(
            Score.is_deleted == 0,
            StudentDB.is_deleted == 0,
            ClassInfo.is_deleted == 0,
        )
        .distinct()
        .order_by(Score.exam_no.asc())
        .all()
    )
    return [row[0] for row in rows]


def get_active_students_by_numbers(
    db: Session, student_numbers: set[str]
) -> dict[str, StudentDB]:
    if not student_numbers:
        return {}
    students = (
        db.query(StudentDB)
        .filter(
            StudentDB.student_no.in_(student_numbers),
            StudentDB.is_deleted == 0,
        )
        .all()
    )
    return {student.student_no: student for student in students}


def get_active_score_keys(
    db: Session,
    keys: set[tuple[int, int]],
    for_update: bool = False,
) -> set[tuple[int, int]]:
    if not keys:
        return set()
    student_ids = {student_id for student_id, _exam_no in keys}
    exam_numbers = {exam_no for _student_id, exam_no in keys}
    query = db.query(Score.student_id, Score.exam_no).filter(
        Score.student_id.in_(student_ids),
        Score.exam_no.in_(exam_numbers),
        Score.is_deleted == 0,
    )
    if for_update:
        query = query.with_for_update()
    rows = query.all()
    return {(student_id, exam_no) for student_id, exam_no in rows} & keys


class ScoreBatchConflict(Exception):
    """批量校验后、提交前数据发生冲突。"""


def create_scores_batch(db: Session, rows: list[dict]):
    """锁定相关学生、复查冲突并在一次事务中插入全部成绩。"""
    student_ids = sorted({row["student_id"] for row in rows})
    keys = {(row["student_id"], row["exam_no"]) for row in rows}
    try:
        locked_students = (
            db.query(StudentDB)
            .filter(
                StudentDB.id.in_(student_ids),
                StudentDB.is_deleted == 0,
            )
            .order_by(StudentDB.id.asc())
            .with_for_update()
            .all()
        )
        if {student.id for student in locked_students} != set(student_ids):
            raise ScoreBatchConflict()
        # 锁定读使用数据库当前版本，避免前置校验后的并发写入被事务快照隐藏。
        if get_active_score_keys(db, keys, for_update=True):
            raise ScoreBatchConflict()
        db.add_all([Score(**row) for row in rows])
        db.commit()
    except Exception:
        db.rollback()
        raise


# 小组原有类式 DAO 兼容层。
class ScoreDAO:
    @staticmethod
    def get_by_id(db: Session, score_id: int):
        return get_score_by_id(db, score_id)

    @staticmethod
    def get_by_student_exam(db: Session, student_id: int, exam_no: int):
        return get_active_score_by_exam(db, student_id, exam_no)

    @staticmethod
    def get_by_student(
        db: Session, student_id: int, exam_no: int | None = None
    ):
        query = db.query(Score).filter(
            Score.student_id == student_id, Score.is_deleted == 0
        )
        if exam_no is not None:
            query = query.filter(Score.exam_no == exam_no)
        return query.order_by(Score.exam_no.asc()).all()

    @staticmethod
    def create(db: Session, student_id: int, exam_no: int, score: Decimal):
        return create_score(
            db,
            {"student_id": student_id, "exam_no": exam_no, "score": score},
        )

    @staticmethod
    def update(
        db: Session,
        score_id: int,
        score: Decimal | None = None,
        exam_no: int | None = None,
    ):
        db_score = get_score_by_id(db, score_id)
        if db_score is None:
            return None
        changes = {}
        if score is not None:
            changes["score"] = score
        if exam_no is not None:
            changes["exam_no"] = exam_no
        return update_score(db, db_score, changes)

    @staticmethod
    def delete(db: Session, score_id: int):
        db_score = get_score_by_id(db, score_id)
        if db_score is None:
            return False
        delete_score(db, db_score)
        return True
