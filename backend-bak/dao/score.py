"""成绩数据访问层"""
from datetime import datetime,UTC
from decimal import Decimal
from sqlalchemy.orm import Session
from model.score import Score
class ScoreDAO:
    @staticmethod
    def get_by_id(db: Session, score_id: int) :
        """根据 ID 查成绩"""
        return db.query(Score).filter(
            Score.id == score_id,
            Score.is_deleted == 0
        ).first()

    @staticmethod
    def get_by_student_exam(
            db: Session,
            student_id: int,
            exam_no: int
    ):
        return db.query(Score).filter(
            Score.student_id == student_id,
            Score.exam_no == exam_no,
            Score.is_deleted == 0
        ).first()

    @staticmethod
    def get_by_student(
            db: Session,
            student_id: int,
            exam_no: int
    ):
        """查学生的成绩列表"""
        query = db.query(Score).filter(
            Score.student_id == student_id,
            Score.is_deleted == 0
        )
        if exam_no is not None:
            query = query.filter(Score.exam_no == exam_no)
        return query.order_by(Score.exam_no).all()

    @staticmethod
    def create(
            db: Session,
            student_id: int,
            exam_no: int,
            score: Decimal
    ):
        """录入成绩"""
        new_score = Score(
            student_id=student_id,
            exam_no=exam_no,
            score=score,
            is_deleted=0
        )
        db.add(new_score)
        db.commit()
        db.refresh(new_score)
        return new_score

    @staticmethod
    def update(
            db: Session,
            score_id: int,
            score: None,
            exam_no:None):
        """修改成绩"""
        db_score = ScoreDAO.get_by_id(db, score_id)
        if not db_score:
            return None
        if score is not None:
            db_score.score = score
        if exam_no is not None:
            db_score.exam_no = exam_no
        db.commit()
        db.refresh(db_score)
        return db_score

    @staticmethod
    def delete(db: Session, score_id: int):
        db_score = ScoreDAO.get_by_id(db, score_id)
        if not db_score:
            return False
        db_score.is_deleted = 1
        db_score.deleted_at = datetime.now(UTC)
        db.commit()
        return True