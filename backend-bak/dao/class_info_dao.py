"""
班级 DAO
========
只负责 classes 表的基础读写，以及班级删除前所需的关联数量查询。
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from database import Base
from model.class_info import ClassInfo, ClassTeacherRelation
from model.students_model import StudentDB

# [修改说明] 原代码：DAO 从不存在的 database.serialize 导入函数，并把查重、老师绑定、物理删除和统计等业务混在 CRUD 中；修改原因：模块无法导入，物理删除破坏历史，且重复 ORM 模型会与其他模块冲突；修改为：保留小组 class_info_dao.py 文件名和兼容辅助函数，基础 CRUD 改为统一逻辑删除、筛选分页和关联计数，业务错误由 API 层处理。


class BusinessError(Exception):
    """保留小组原异常类型，供尚未迁移的调用方兼容。"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def get_class_by_id(db: Session, class_id: int):
    """按主键查询未删除班级。"""
    return (
        db.query(ClassInfo)
        .filter(ClassInfo.id == class_id, ClassInfo.is_deleted == 0)
        .first()
    )


def get_class_by_no(db: Session, class_no: str):
    """按班号查询，包含已删除数据，用于保证班号全表唯一。"""
    return db.query(ClassInfo).filter(ClassInfo.class_no == class_no).first()


def get_class(db: Session, class_no: str):
    """兼容小组原函数名：按班号查询未删除班级。"""
    return (
        db.query(ClassInfo)
        .filter(
            ClassInfo.class_no == class_no,
            ClassInfo.is_deleted == 0,
        )
        .first()
    )


def list_classes(
    db: Session,
    page: int,
    page_size: int,
    class_no: str | None = None,
    class_name: str | None = None,
    class_status: str | None = None,
):
    """按班号、名称和状态筛选未删除班级，返回（当前页，总数）。"""
    class_no = clean_text(class_no)
    class_name = clean_text(class_name)
    class_status = clean_text(class_status)

    query = db.query(ClassInfo).filter(ClassInfo.is_deleted == 0)
    if class_no is not None:
        query = query.filter(ClassInfo.class_no == class_no)
    if class_name is not None:
        query = query.filter(ClassInfo.class_name.like(f"%{class_name}%"))
    if class_status is not None:
        query = query.filter(ClassInfo.class_status == class_status)

    query = query.order_by(ClassInfo.id.asc())
    return paginate(query, page, page_size)


def list_all_classes(db: Session):
    """返回全部未删除班级，供统计模块复用。"""
    return (
        db.query(ClassInfo)
        .filter(ClassInfo.is_deleted == 0)
        .order_by(ClassInfo.id.asc())
        .all()
    )


def create_class(db: Session, data: dict):
    """新增班级。"""
    class_info = ClassInfo(**data)
    db.add(class_info)
    db.commit()
    db.refresh(class_info)
    return class_info


# [修改说明] 原代码：create_class 只能单独提交 classes 记录；修改原因：建班表单同时提交教学团队时，逐条调用关系接口会在中途失败后留下半成品；修改为：新增兼容事务函数，在一次提交中写班级及全部关系，原 create_class 保留给无排班调用方。
def create_class_with_relations(db: Session, data: dict, relations: list[dict]):
    """在同一事务中新增班级和初始老师关系。"""
    class_info = ClassInfo(**data)
    try:
        db.add(class_info)
        db.flush()
        for relation_data in relations:
            db.add(
                ClassTeacherRelation(
                    class_id=class_info.id,
                    teacher_id=relation_data["teacher_id"],
                    relation_type=relation_data["relation_type"],
                )
            )
        db.commit()
        db.refresh(class_info)
        return class_info
    except Exception:
        db.rollback()
        raise


def update_class(db: Session, class_info: ClassInfo, changes: dict):
    """只更新 changes 中出现的字段。"""
    for field_name, value in changes.items():
        setattr(class_info, field_name, value)
    db.commit()
    db.refresh(class_info)
    return class_info


def count_students_by_class(db: Session, class_id: int):
    """统计班级下未删除学生数量。"""
    return (
        db.query(StudentDB)
        .filter(
            StudentDB.class_id == class_id,
            StudentDB.is_deleted.is_(False),
        )
        .count()
    )


def count_relations_by_class(db: Session, class_id: int):
    """统计班级的有效老师关系数量。"""
    return (
        db.query(ClassTeacherRelation)
        .filter(
            ClassTeacherRelation.class_id == class_id,
            ClassTeacherRelation.is_deleted == 0,
        )
        .count()
    )


def delete_class(db: Session, class_info: ClassInfo):
    """逻辑删除班级。"""
    class_info.is_deleted = 1
    class_info.deleted_at = datetime.now()
    db.commit()


def class_to_dict(class_info: ClassInfo):
    """兼容小组原辅助函数，不再依赖不存在的 database.serialize。"""
    return {
        column.name: getattr(class_info, column.name)
        for column in ClassInfo.__table__.columns
    }


# [修改说明] 原代码：通过本文件中重复定义的简化 Teacher 模型逐条查询老师姓名；修改原因：该模型会与正式老师表重复映射，且形成 N+1 查询；修改为：兼容函数仅返回有效关系中的 teacher_id 和 relation_type，完整老师资料由后续排班接口统一联表返回。
def get_class_with_teachers(db: Session, class_no: str):
    """兼容原班号详情函数，返回班级及有效关系的老师 ID。"""
    class_info = get_class(db, class_no)
    if class_info is None:
        return None

    relations = (
        db.query(ClassTeacherRelation)
        .filter(
            ClassTeacherRelation.class_id == class_info.id,
            ClassTeacherRelation.is_deleted == 0,
        )
        .order_by(ClassTeacherRelation.id.asc())
        .all()
    )
    data = class_to_dict(class_info)
    data["teachers"] = [
        {"teacher_id": relation.teacher_id, "relation_type": relation.relation_type}
        for relation in relations
    ]
    return data


# [修改说明] 原代码：统计函数依赖本文件里重复定义的简化 Student/Score 模型；修改原因：启用正式学生和成绩模型后会产生表冲突；修改为：学生使用小组现有 StudentDB，成绩通过已注册的 scores 元数据读取，成绩模块尚未接入时安全返回零成绩。
def get_class_statistics(db: Session, class_no: str):
    """保留小组原扩展统计接口；成绩模型接入前按无成绩处理。"""
    class_info = get_class(db, class_no)
    if class_info is None:
        return None

    student_ids = [
        row.id
        for row in db.query(StudentDB.id)
        .filter(
            StudentDB.class_id == class_info.id,
            StudentDB.is_deleted.is_(False),
        )
        .all()
    ]

    score_table = Base.metadata.tables.get("scores")
    score_values = []
    if student_ids and score_table is not None:
        statement = select(score_table.c.score).where(
            score_table.c.student_id.in_(student_ids),
            score_table.c.is_deleted == 0,
        )
        score_values = list(db.execute(statement).scalars())

    pass_count = sum(1 for score in score_values if score is not None and score >= 60)
    pass_rate = round(pass_count / len(score_values) * 100, 2) if score_values else 0
    return {
        "class_no": class_info.class_no,
        "class_name": class_info.class_name,
        "total_students": len(student_ids),
        "total_scores": len(score_values),
        "pass_count": pass_count,
        "pass_rate": f"{pass_rate}%",
    }
