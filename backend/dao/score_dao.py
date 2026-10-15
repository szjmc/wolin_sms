"""
成绩数据访问层：只负责 scores 表的增删改查，不写业务判断
"""
from datetime import datetime

from sqlalchemy.orm import Session

from dao.common import paginate
from model.score import Score


def get_score_by_id(db: Session, score_id: int):
    """
    根据成绩主键 ID 查询一条未删除成绩。
    业务接口不要走这个方法：老师改成绩请用 get_active_score_by_exam（学生 + 考核序次）。
    """
    return (
        db.query(Score)
        .filter(Score.id == score_id, Score.is_deleted == 0)
        .first()
    )


def get_active_score_by_exam(db: Session, student_id: int, exam_no: int):
    """
    按「学生ID + 考核序次」查询一条未删除的成绩，查不到返回 None。

    这是成绩模块的业务主键查询方法：
    老师改成绩、查成绩、删成绩都走这里，而不是按成绩表自增 id 查找。
    同一学生同一考核序次在未删除数据中最多只有一条。
    """
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
    """分页查询某个学生的未删除成绩，按考核序次排序，返回 (当前页成绩列表, 总条数)"""
    query = db.query(Score).filter(Score.student_id == student_id, Score.is_deleted == 0)
    if exam_no is not None:
        query = query.filter(Score.exam_no == exam_no)

    query = query.order_by(Score.exam_no.asc(), Score.id.asc())
    return paginate(query, page, page_size)


def create_score(db: Session, data: dict):
    """新增成绩"""
    score = Score(**data)
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def update_score(db: Session, score: Score, changes: dict):
    """修改成绩：只修改 changes 里出现的字段"""
    for field_name, value in changes.items():
        setattr(score, field_name, value)
    db.commit()
    db.refresh(score)
    return score


def delete_score(db: Session, score: Score):
    """逻辑删除成绩"""
    score.is_deleted = 1
    score.deleted_at = datetime.now()
    db.commit()
