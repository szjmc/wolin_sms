from datetime import date, datetime
from typing import Optional
from fastapi import Query, APIRouter
from sqlalchemy.orm import declarative_base, sessionmaker,Session
from model.students_model import StudentDB
from scheme.students import Gender
router = APIRouter()


# ---------------- 工具函数 计算年龄 ----------------
def calc_age(birth: Optional[date]) -> Optional[int]:
    if birth is None:
        return None
    today = date.today()
    age = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        age -= 1
    return age


def get_stu_no(db:Session,stu_id:str):
    return (db.query(StudentDB).filter(
        StudentDB.student_no == stu_id
    ).first())


def select_stu_list(db:Session,
               page:int,
               page_size:int,
               student_no:str,
               name:str,
               class_id:int,
               gender:Gender):
    q = db.query(StudentDB).filter(StudentDB.is_deleted == False)

    if student_no:
        q = q.filter(StudentDB.student_no.like(f"%{student_no}%"))

    if name:
        q = q.filter(StudentDB.name.like(f"%{name}%"))

    if class_id is not None:
        q = q.filter(StudentDB.class_id == class_id)

    if gender:
        q = q.filter(StudentDB.gender == gender.value)

    total = q.count()

    records = q.offset((page - 1) * page_size).limit(page_size).all()

    return total,records


def update_student_db(stu: StudentDB, update_dict: dict, db: Session):
    try:
        for field, value in update_dict.items():
            if hasattr(stu, field):
                setattr(stu, field, value)
        # hasattr() 是 Python 内置函数，用来判断一个对象是否具有某个属性
        # setattr() 也是 Python 内置函数，用来动态设置对象的属性

        db.commit()
        db.refresh(stu)
        return stu

    except Exception:
        db.rollback()
        raise








