"""
班级老师关系数据访问层：只负责 class_teacher_relations 表的增删改查，不写业务判断

新版排班规则（接口层用下面的查询函数来实现，见 api/class_teacher_api.py）：
1. 一个老师同一时间只能负责一个未结课班级（不管是班主任还是授课老师）
2. 同一个班级里，班主任和授课老师不能是同一人
3. 一个班级最多只能有一位在任班主任
"""
from datetime import datetime

from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from model.class_info import ClassInfo
from model.class_teacher_relation import ClassTeacherRelation
from model.teacher import Teacher


def get_active_relation(db: Session, class_id: int, teacher_id: int, relation_type: str):
    """查询一条"有效（未删除）"的班级老师关系，查不到返回 None"""
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


def get_teacher_busy_relation(db: Session, teacher_id: int):
    """
    查询某个老师当前占用的排班（只看未结课班级），查不到返回 None。

    判定“占用”的三个条件要同时满足：
    关系本身未删除 + 班级未删除 + 班级状态不是“已结课”。
    已结课班级的历史关系不算占用，老师可以去带新班级。
    """
    return (
        db.query(ClassTeacherRelation)
        .join(ClassInfo, ClassInfo.id == ClassTeacherRelation.class_id)
        .filter(
            ClassTeacherRelation.teacher_id == teacher_id,
            ClassTeacherRelation.is_deleted == 0,
            ClassInfo.is_deleted == 0,
            ClassInfo.class_status != "已结课",
        )
        .first()
    )


def get_class_active_head(db: Session, class_id: int):
    """查询某个班级当前在任的班主任关系，查不到返回 None（说明该班级还没有班主任）"""
    return (
        db.query(ClassTeacherRelation)
        .filter(
            ClassTeacherRelation.class_id == class_id,
            ClassTeacherRelation.relation_type == "班主任",
            ClassTeacherRelation.is_deleted == 0,
        )
        .first()
    )


def list_active_relations(db: Session, class_id: int, teacher_id: int, relation_type: str | None = None):
    """
    查询某个班级和某个老师之间的所有有效关系。
    relation_type 为 None 时返回全部关系类型。
    """
    relation_type = clean_text(relation_type)
    query = db.query(ClassTeacherRelation).filter(
        ClassTeacherRelation.class_id == class_id,
        ClassTeacherRelation.teacher_id == teacher_id,
        ClassTeacherRelation.is_deleted == 0,
    )
    if relation_type is not None:
        query = query.filter(ClassTeacherRelation.relation_type == relation_type)
    return query.order_by(ClassTeacherRelation.id.asc()).all()


def list_class_teachers(db: Session, class_id: int, page: int, page_size: int):
    """
    分页查询某个班级的有效老师关系，同时带出老师信息。
    返回 (当前页数据, 总条数)，当前页的每一行是 (关系对象, 老师对象)。
    """
    query = (
        db.query(ClassTeacherRelation, Teacher)
        .join(Teacher, Teacher.id == ClassTeacherRelation.teacher_id)
        .filter(
            ClassTeacherRelation.class_id == class_id,
            ClassTeacherRelation.is_deleted == 0,
            Teacher.is_deleted == 0,
        )
    )

    query = query.order_by(ClassTeacherRelation.id.asc())
    return paginate(query, page, page_size)


def count_relations_by_class(db: Session, class_id: int):
    """统计某个班级的有效老师关系数量（删除班级前检查使用）"""
    return (
        db.query(ClassTeacherRelation)
        .filter(ClassTeacherRelation.class_id == class_id, ClassTeacherRelation.is_deleted == 0)
        .count()
    )


def count_relations_by_teacher(db: Session, teacher_id: int):
    """统计某个老师的有效班级关系数量（删除老师前检查使用）"""
    return (
        db.query(ClassTeacherRelation)
        .filter(ClassTeacherRelation.teacher_id == teacher_id, ClassTeacherRelation.is_deleted == 0)
        .count()
    )


def create_relation(db: Session, data: dict):
    """新增一条班级老师关系"""
    relation = ClassTeacherRelation(**data)
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation


def delete_relations(db: Session, relations: list):
    """逻辑删除一批班级老师关系（在同一个事务里提交）"""
    now = datetime.now()
    for relation in relations:
        relation.is_deleted = 1
        relation.deleted_at = now
    db.commit()
