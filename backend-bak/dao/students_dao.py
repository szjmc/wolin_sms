"""学生数据访问层：负责 students 表的基础增删改查。"""
from datetime import date, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from model.students_model import StudentDB


# [修改说明] 原代码：DAO 只支持按学号查询，列表参数全部必传且 gender 被重复取 .value，更新函数也未被接口调用；修改原因：会导致列表空条件报错、性别筛选异常和 PATCH 实际不保存；修改为：保留 students_dao.py 与兼容函数名，补齐按 ID CRUD、统一分页、组合搜索、年龄日期筛选及逻辑删除。
def get_student_by_id(db: Session, student_id: int):
    """按主键查询未删除学生。"""
    return (
        db.query(StudentDB)
        .filter(StudentDB.id == student_id, StudentDB.is_deleted == 0)
        .first()
    )


def get_student_by_no(db: Session, student_no: str):
    """按学生编号查询，包含已删除记录，用于保证编号全表唯一。"""
    return db.query(StudentDB).filter(StudentDB.student_no == student_no).first()


def list_students(
    db: Session,
    page: int,
    page_size: int,
    student_no: str | None = None,
    name: str | None = None,
    class_id: int | None = None,
    gender: str | None = None,
    max_birth_date: date | None = None,
    q: str | None = None,
):
    """分页查询未删除学生；所有筛选条件按 AND 组合。"""
    student_no = clean_text(student_no)
    name = clean_text(name)
    gender = clean_text(gender)
    q = clean_text(q)

    query = db.query(StudentDB).filter(StudentDB.is_deleted == 0)
    if q is not None:
        keyword = f"%{q}%"
        query = query.filter(
            or_(StudentDB.student_no.like(keyword), StudentDB.name.like(keyword))
        )
    if student_no is not None:
        query = query.filter(StudentDB.student_no == student_no)
    if name is not None:
        query = query.filter(StudentDB.name.like(f"%{name}%"))
    if class_id is not None:
        query = query.filter(StudentDB.class_id == class_id)
    if gender is not None:
        query = query.filter(StudentDB.gender == gender)
    if max_birth_date is not None:
        query = query.filter(StudentDB.birth_date <= max_birth_date)

    query = query.order_by(StudentDB.id.asc())
    return paginate(query, page, page_size)


def list_students_by_ids(db: Session, student_ids: list[int]):
    """按一批 ID 查询未删除学生，供统计模块复用。"""
    if not student_ids:
        return []
    return (
        db.query(StudentDB)
        .filter(StudentDB.id.in_(student_ids), StudentDB.is_deleted == 0)
        .order_by(StudentDB.id.asc())
        .all()
    )


def count_students_by_class(db: Session, class_id: int) -> int:
    """统计班级内未删除学生数量。"""
    return (
        db.query(StudentDB)
        .filter(StudentDB.class_id == class_id, StudentDB.is_deleted == 0)
        .count()
    )


def create_student(db: Session, data: dict):
    """新增学生。"""
    student = StudentDB(**data)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def update_student(db: Session, student: StudentDB, changes: dict):
    """仅更新请求中实际出现的字段。"""
    for field_name, value in changes.items():
        setattr(student, field_name, value)
    db.commit()
    db.refresh(student)
    return student


def delete_student(db: Session, student: StudentDB):
    """逻辑删除学生，关联成绩、经历及就业历史继续保留。"""
    student.is_deleted = 1
    student.deleted_at = datetime.now()
    db.commit()


# 以下兼容小组原函数名，避免尚未迁移的模块导入失败。
def calc_age(birth: date | None) -> int | None:
    if birth is None:
        return None
    today = date.today()
    age = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        age -= 1
    return age


def get_stu_no(db: Session, stu_id: str):
    return get_student_by_no(db, stu_id)


def select_stu_list(
    db: Session,
    page: int,
    page_size: int,
    student_no: str | None = None,
    name: str | None = None,
    class_id: int | None = None,
    gender=None,
):
    gender_value = getattr(gender, "value", gender)
    records, total = list_students(
        db,
        page,
        page_size,
        student_no=student_no,
        name=name,
        class_id=class_id,
        gender=gender_value,
    )
    return total, records


def update_student_db(stu: StudentDB, update_dict: dict, db: Session):
    return update_student(db, stu, update_dict)
