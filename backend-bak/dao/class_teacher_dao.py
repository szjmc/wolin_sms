"""班级—老师关系数据访问层。"""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from dao.common import paginate
from model.class_info import ClassInfo, ClassTeacherRelation
from model.teacher import Teacher


# [修改说明] 原代码：本文件只有删除保护所需的两个计数函数；修改原因：关系模块无法查询、创建、幂等判断或逻辑解除排班；修改为：保留原计数职责，并按 backend 的查询边界补齐完整关系 DAO，事务和业务规则仍由 API 层统一控制。
def get_active_relation(
    db: Session,
    class_id: int,
    teacher_id: int,
    relation_type: str,
) -> ClassTeacherRelation | None:
    """获取完全相同的有效关系，用于 PUT 幂等。"""
    return (
        db.query(ClassTeacherRelation)
        .filter(
            ClassTeacherRelation.class_id == class_id,
            ClassTeacherRelation.teacher_id == teacher_id,
            ClassTeacherRelation.relation_type == relation_type,
            ClassTeacherRelation.is_deleted == 0,
        )
        .first()
    )


def get_teacher_busy_relation(
    db: Session,
    teacher_id: int,
    exclude_class_id: int | None = None,
) -> ClassTeacherRelation | None:
    """查找老师在任一未结课班级中的有效角色。"""
    query = (
        db.query(ClassTeacherRelation)
        .join(ClassInfo, ClassInfo.id == ClassTeacherRelation.class_id)
        .filter(
            ClassTeacherRelation.teacher_id == teacher_id,
            ClassTeacherRelation.is_deleted == 0,
            ClassInfo.is_deleted == 0,
            ClassInfo.class_status != "已结课",
        )
    )
    if exclude_class_id is not None:
        query = query.filter(ClassTeacherRelation.class_id != exclude_class_id)
    return query.order_by(ClassTeacherRelation.id.asc()).first()


def get_class_active_head_teacher(db: Session, class_id: int) -> ClassTeacherRelation | None:
    """获取班级当前有效班主任。"""
    return (
        db.query(ClassTeacherRelation)
        .filter(
            ClassTeacherRelation.class_id == class_id,
            ClassTeacherRelation.relation_type == "班主任",
            ClassTeacherRelation.is_deleted == 0,
        )
        .order_by(ClassTeacherRelation.id.asc())
        .first()
    )


def get_active_relation_for_teacher_in_class(
    db: Session,
    class_id: int,
    teacher_id: int,
) -> ClassTeacherRelation | None:
    """查找老师在指定班级中的任一有效角色。"""
    return (
        db.query(ClassTeacherRelation)
        .filter(
            ClassTeacherRelation.class_id == class_id,
            ClassTeacherRelation.teacher_id == teacher_id,
            ClassTeacherRelation.is_deleted == 0,
        )
        .order_by(ClassTeacherRelation.id.asc())
        .first()
    )


def create_relation(
    db: Session,
    class_id: int,
    teacher_id: int,
    relation_type: str,
) -> ClassTeacherRelation:
    """新增关系；被解除的历史记录不复活，而是保留后再插入新记录。"""
    relation = ClassTeacherRelation(
        class_id=class_id,
        teacher_id=teacher_id,
        relation_type=relation_type,
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation


def list_class_teacher_rows(
    db: Session,
    class_id: int,
) -> list[tuple[ClassTeacherRelation, Teacher]]:
    """返回指定班级全部有效关系及老师信息。"""
    return (
        db.query(ClassTeacherRelation, Teacher)
        .join(Teacher, Teacher.id == ClassTeacherRelation.teacher_id)
        .filter(
            ClassTeacherRelation.class_id == class_id,
            ClassTeacherRelation.is_deleted == 0,
            Teacher.is_deleted == 0,
        )
        .order_by(ClassTeacherRelation.id.asc())
        .all()
    )


def list_class_teachers(
    db: Session,
    class_id: int,
    relation_type: str | None,
    page: int,
    page_size: int,
) -> tuple[list[tuple[ClassTeacherRelation, Teacher]], int]:
    """分页查询一个班级的有效老师关系。"""
    query = (
        db.query(ClassTeacherRelation, Teacher)
        .join(Teacher, Teacher.id == ClassTeacherRelation.teacher_id)
        .filter(
            ClassTeacherRelation.class_id == class_id,
            ClassTeacherRelation.is_deleted == 0,
            Teacher.is_deleted == 0,
        )
    )
    if relation_type:
        query = query.filter(ClassTeacherRelation.relation_type == relation_type)
    query = query.order_by(ClassTeacherRelation.id.asc())
    return paginate(query, page, page_size)


def list_teacher_relation_rows(
    db: Session,
    teacher_id: int,
) -> list[tuple[ClassTeacherRelation, ClassInfo, Teacher]]:
    """查询老师详情所需的全部当前有效关系。"""
    return (
        db.query(ClassTeacherRelation, ClassInfo, Teacher)
        .join(ClassInfo, ClassInfo.id == ClassTeacherRelation.class_id)
        .join(Teacher, Teacher.id == ClassTeacherRelation.teacher_id)
        .filter(
            ClassTeacherRelation.teacher_id == teacher_id,
            ClassTeacherRelation.is_deleted == 0,
            ClassInfo.is_deleted == 0,
            Teacher.is_deleted == 0,
        )
        .order_by(ClassTeacherRelation.id.asc())
        .all()
    )


def list_relation_overview_rows(
    db: Session,
    page: int,
    page_size: int,
    class_id: int | None = None,
    teacher_id: int | None = None,
    relation_type: str | None = None,
    class_keyword: str | None = None,
    teacher_keyword: str | None = None,
    class_status: str | None = None,
    teacher_status: str | None = None,
    teaching_status: str | None = None,
) -> tuple[list[tuple[ClassTeacherRelation, ClassInfo, Teacher]], int]:
    """分页查询排班管理页所需的班级、老师、关系联合数据。"""
    query = (
        db.query(ClassTeacherRelation, ClassInfo, Teacher)
        .join(ClassInfo, ClassInfo.id == ClassTeacherRelation.class_id)
        .join(Teacher, Teacher.id == ClassTeacherRelation.teacher_id)
        .filter(
            ClassTeacherRelation.is_deleted == 0,
            ClassInfo.is_deleted == 0,
            Teacher.is_deleted == 0,
        )
    )
    if class_id is not None:
        query = query.filter(ClassTeacherRelation.class_id == class_id)
    if teacher_id is not None:
        query = query.filter(ClassTeacherRelation.teacher_id == teacher_id)
    if relation_type:
        query = query.filter(ClassTeacherRelation.relation_type == relation_type)
    if class_keyword:
        keyword = f"%{class_keyword.strip()}%"
        query = query.filter(
            or_(ClassInfo.class_no.like(keyword), ClassInfo.class_name.like(keyword))
        )
    if teacher_keyword:
        keyword = f"%{teacher_keyword.strip()}%"
        query = query.filter(
            or_(Teacher.teacher_no.like(keyword), Teacher.name.like(keyword))
        )
    if class_status:
        query = query.filter(ClassInfo.class_status == class_status)
    if teacher_status:
        query = query.filter(Teacher.teacher_status == teacher_status)
    if teaching_status:
        query = query.filter(Teacher.teaching_status == teaching_status)

    query = query.order_by(
        ClassInfo.class_no.asc(),
        ClassTeacherRelation.relation_type.asc(),
        ClassTeacherRelation.id.asc(),
    )
    return paginate(query, page, page_size)


def soft_delete_relations(
    db: Session,
    class_id: int,
    teacher_id: int,
    relation_type: str | None = None,
) -> int:
    """逻辑解除关系；未传关系类型时解除该老师在班级内的全部有效角色。"""
    query = db.query(ClassTeacherRelation).filter(
        ClassTeacherRelation.class_id == class_id,
        ClassTeacherRelation.teacher_id == teacher_id,
        ClassTeacherRelation.is_deleted == 0,
    )
    if relation_type:
        query = query.filter(ClassTeacherRelation.relation_type == relation_type)

    now = datetime.now()
    affected = query.update(
        {
            ClassTeacherRelation.is_deleted: 1,
            ClassTeacherRelation.deleted_at: now,
            ClassTeacherRelation.updated_at: now,
        },
        synchronize_session=False,
    )
    db.commit()
    return affected


def count_active_relations_for_class(db: Session, class_id: int) -> int:
    """统计班级当前有效老师关系，供班级删除保护使用。"""
    return (
        db.query(ClassTeacherRelation)
        .filter(
            ClassTeacherRelation.class_id == class_id,
            ClassTeacherRelation.is_deleted == 0,
        )
        .count()
    )


def count_active_relations_for_teacher(db: Session, teacher_id: int) -> int:
    """统计老师当前有效班级关系，供老师删除保护使用。"""
    return (
        db.query(ClassTeacherRelation)
        .filter(
            ClassTeacherRelation.teacher_id == teacher_id,
            ClassTeacherRelation.is_deleted == 0,
        )
        .count()
    )


# [修改说明] 原代码：老师接口调用 count_relations_by_teacher；修改原因：补全 DAO 时使用了更明确的 active 命名会破坏已有调用；修改为：保留兼容别名并统一委托给有效关系计数，原老师删除逻辑无需改写。
def count_relations_by_teacher(db: Session, teacher_id: int) -> int:
    return count_active_relations_for_teacher(db, teacher_id)


def count_relations_by_class(db: Session, class_id: int) -> int:
    return count_active_relations_for_class(db, class_id)
