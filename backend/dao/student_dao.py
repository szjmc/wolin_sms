"""
学生数据访问层：只负责 students 表的增删改查，不写业务判断
"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from model.student import Student


def get_student_by_id(db: Session, student_id: int):
    """根据ID查询一个未删除的学生，查不到返回 None"""
    return (
        db.query(Student)
        .filter(Student.id == student_id, Student.is_deleted == 0)
        .first()
    )


def get_student_by_no(db: Session, student_no: str):
    """
    根据学生编号查询学生（注意：包含已逻辑删除的学生）。
    只用于新增时检查编号是否重复——数据库唯一索引对已删除的记录同样生效。
    """
    return db.query(Student).filter(Student.student_no == student_no).first()


def list_students(
    db: Session,
    page: int,
    page_size: int,
    student_no: str | None = None,
    name: str | None = None,
    class_id: int | None = None,
    gender: str | None = None,
    max_birth_date: date | None = None,
):
    """
    分页查询未删除的学生，返回 (当前页学生列表, 总条数)。
    筛选参数为 None（或空字符串）表示不按这个条件筛选。
    max_birth_date：出生日期上限，用来实现"年龄大于 N 岁"的筛选（出生日期 <= 上限）。
    注意：筛选参数的 None 只表示“不过滤”。学生编号、姓名这些数据库字段本身是必填的，不会存成空。
    """
    student_no = clean_text(student_no)
    name = clean_text(name)
    gender = clean_text(gender)

    query = db.query(Student).filter(Student.is_deleted == 0)
    if student_no is not None:
        query = query.filter(Student.student_no == student_no)
    if name is not None:
        query = query.filter(Student.name.like(f"%{name}%"))
    if class_id is not None:
        query = query.filter(Student.class_id == class_id)
    if gender is not None:
        query = query.filter(Student.gender == gender)
    if max_birth_date is not None:
        query = query.filter(Student.birth_date <= max_birth_date)

    query = query.order_by(Student.id.asc())
    return paginate(query, page, page_size)


def list_students_by_ids(db: Session, student_ids: list):
    """根据一批学生ID查询未删除的学生（统计接口使用）"""
    if len(student_ids) == 0:
        return []
    return (
        db.query(Student)
        .filter(Student.id.in_(student_ids), Student.is_deleted == 0)
        .order_by(Student.id.asc())
        .all()
    )


def count_students_by_class(db: Session, class_id: int):
    """统计某个班级下未删除的学生人数（删除班级前检查使用）"""
    return (
        db.query(Student)
        .filter(Student.class_id == class_id, Student.is_deleted == 0)
        .count()
    )


def create_student(db: Session, data: dict):
    """新增学生"""
    student = Student(**data)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def update_student(db: Session, student: Student, changes: dict):
    """更新学生：只修改 changes 里出现的字段"""
    for field_name, value in changes.items():
        setattr(student, field_name, value)
    db.commit()
    db.refresh(student)
    return student


def delete_student(db: Session, student: Student):
    """
    逻辑删除学生。
    只给学生本人打删除标记；成绩、过往经历、就业记录不做任何修改，全部保留。
    """
    student.is_deleted = 1
    student.deleted_at = datetime.now()
    db.commit()
