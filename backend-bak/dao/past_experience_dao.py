"""
学生过往经历数据访问层：只负责 student_past_experiences 表的增删改查，不写业务判断
"""
from datetime import datetime

from sqlalchemy.orm import Session

from dao.common import paginate
from model.past_experience import StudentPastExperience


def get_experience_by_id(db: Session, experience_id: int):
    """根据ID查询一条未删除的过往经历，查不到返回 None"""
    return (
        db.query(StudentPastExperience)
        .filter(StudentPastExperience.id == experience_id, StudentPastExperience.is_deleted == 0)
        .first()
    )


def list_experiences_by_student(db: Session, student_id: int, page: int, page_size: int):
    """分页查询某个学生的未删除过往经历（必须按 student_id 过滤），返回 (当前页列表, 总条数)"""
    query = db.query(StudentPastExperience).filter(
        StudentPastExperience.student_id == student_id,
        StudentPastExperience.is_deleted == 0,
    )

    query = query.order_by(StudentPastExperience.id.asc())
    return paginate(query, page, page_size)


def create_experience(db: Session, data: dict):
    """新增过往经历"""
    experience = StudentPastExperience(**data)
    db.add(experience)
    db.commit()
    db.refresh(experience)
    return experience


def update_experience(db: Session, experience: StudentPastExperience, changes: dict):
    """修改过往经历：只修改 changes 里出现的字段"""
    for field_name, value in changes.items():
        setattr(experience, field_name, value)
    db.commit()
    db.refresh(experience)
    return experience


def delete_experience(db: Session, experience: StudentPastExperience):
    """逻辑删除过往经历（只影响这一条，不影响该学生的其他经历）"""
    experience.is_deleted = 1
    experience.deleted_at = datetime.now()
    db.commit()
