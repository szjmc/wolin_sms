"""学生过往经历数据访问层。"""
from datetime import datetime

from sqlalchemy.orm import Session

from dao.common import paginate
from model.past_experience import StudentPastExperience


def get_experience_by_id(db: Session, experience_id: int):
    """按主键查询一条未删除经历。"""
    return (
        db.query(StudentPastExperience)
        .filter(
            StudentPastExperience.id == experience_id,
            StudentPastExperience.is_deleted == 0,
        )
        .first()
    )


def list_experiences_by_student(
    db: Session,
    student_id: int,
    page: int,
    page_size: int,
):
    """分页查询指定学生的全部有效经历。"""
    query = (
        db.query(StudentPastExperience)
        .filter(
            StudentPastExperience.student_id == student_id,
            StudentPastExperience.is_deleted == 0,
        )
        .order_by(StudentPastExperience.id.asc())
    )
    return paginate(query, page, page_size)


# [修改说明] 原代码：DAO 只能分页读取全部过往经历；修改原因：新增就业记录需要在未显式提交快照时原子地选取最近一条有效经历；修改为：补充按主键倒序读取最近有效记录的只读函数，原列表排序及 CRUD 保持不变。
def get_latest_experience_by_student(db: Session, student_id: int):
    """读取学生最近新增的一条有效过往经历，供就业创建时复制快照。"""
    return (
        db.query(StudentPastExperience)
        .filter(
            StudentPastExperience.student_id == student_id,
            StudentPastExperience.is_deleted == 0,
        )
        .order_by(StudentPastExperience.id.desc())
        .first()
    )


def create_experience(db: Session, data: dict):
    experience = StudentPastExperience(**data)
    db.add(experience)
    db.commit()
    db.refresh(experience)
    return experience


def update_experience(
    db: Session,
    experience: StudentPastExperience,
    changes: dict,
):
    for field_name, value in changes.items():
        setattr(experience, field_name, value)
    db.commit()
    db.refresh(experience)
    return experience


def delete_experience(db: Session, experience: StudentPastExperience):
    """只逻辑删除当前记录，不影响同一学生的其他经历。"""
    experience.is_deleted = 1
    experience.deleted_at = datetime.now()
    db.commit()
