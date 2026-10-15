"""
老师数据访问层：只负责 teachers 表的增删改查，不写业务判断
"""
from datetime import datetime

from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from model.teacher import Teacher

# [修改说明] 原代码：列表查询在每个 DAO 内重复 count/offset/limit，且空白筛选值没有统一清洗；修改原因：与其他模块分页口径不一致，传入仅含空格的条件会造成误过滤；修改为：保留 dao/teacher.py 和现有 CRUD，列表接入公共 clean_text 与 paginate。


def get_teacher_by_id(db: Session, teacher_id: int):
    """根据ID查询一个未删除的老师，查不到返回 None"""
    return (
        db.query(Teacher)
        .filter(Teacher.id == teacher_id, Teacher.is_deleted == 0)
        .first()
    )


def get_teacher_by_no(db: Session, teacher_no: str):
    """
    根据老师编号查询老师（注意：包含已逻辑删除的老师）。
    只用于新增时检查编号是否重复。
    """
    return db.query(Teacher).filter(Teacher.teacher_no == teacher_no).first()


def list_teachers(
    db: Session,
    page: int,
    page_size: int,
    teacher_no: str | None = None,
    name: str | None = None,
    specialty: str | None = None,
    teacher_status: str | None = None,
    # [修改说明] 原代码：老师列表只能按任职状态筛选；修改原因：排班页选择器必须只查询“可授课”老师；修改为：追加可选 teaching_status 筛选参数，不影响原调用方。
    teaching_status: str | None = None,
):
    """分页查询未删除的老师，返回（当前页老师列表，总条数）。"""
    teacher_no = clean_text(teacher_no)
    name = clean_text(name)
    specialty = clean_text(specialty)
    teacher_status = clean_text(teacher_status)
    teaching_status = clean_text(teaching_status)

    query = db.query(Teacher).filter(Teacher.is_deleted == 0)
    if teacher_no is not None:
        query = query.filter(Teacher.teacher_no == teacher_no)
    if name is not None:
        query = query.filter(Teacher.name.like(f"%{name}%"))
    if specialty is not None:
        query = query.filter(Teacher.specialty.like(f"%{specialty}%"))
    if teacher_status is not None:
        query = query.filter(Teacher.teacher_status == teacher_status)
    if teaching_status is not None:
        query = query.filter(Teacher.teaching_status == teaching_status)

    query = query.order_by(Teacher.id.asc())
    return paginate(query, page, page_size)


def create_teacher(db: Session, data: dict):
    """新增老师"""
    teacher = Teacher(**data)
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


def update_teacher(db: Session, teacher: Teacher, changes: dict):
    """更新老师：只修改 changes 里出现的字段"""
    for field_name, value in changes.items():
        setattr(teacher, field_name, value)
    db.commit()
    db.refresh(teacher)
    return teacher


def delete_teacher(db: Session, teacher: Teacher):
    """逻辑删除老师"""
    teacher.is_deleted = 1
    teacher.deleted_at = datetime.now()
    db.commit()
