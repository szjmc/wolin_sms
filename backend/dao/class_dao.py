"""
班级数据访问层：只负责 classes 表的增删改查，不写业务判断
"""
from datetime import datetime

from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from model.class_info import ClassInfo


def get_class_by_id(db: Session, class_id: int):
    """根据ID查询一个未删除的班级，查不到返回 None"""
    return (
        db.query(ClassInfo)
        .filter(ClassInfo.id == class_id, ClassInfo.is_deleted == 0)
        .first()
    )


def get_class_by_no(db: Session, class_no: str):
    """
    根据班级编号查询班级（注意：包含已逻辑删除的班级）。
    只用于新增时检查编号是否重复——数据库唯一索引对已删除的记录同样生效。
    """
    return db.query(ClassInfo).filter(ClassInfo.class_no == class_no).first()


def list_classes(
    db: Session,
    page: int,
    page_size: int,
    class_no: str | None = None,
    class_name: str | None = None,
    class_status: str | None = None,
):
    """
    分页查询未删除的班级，返回 (当前页班级列表, 总条数)。
    筛选参数为 None（或空字符串）表示不按这个条件筛选。
    注意：筛选参数的 None 只表示“不过滤”，和数据库字段是否必填没有关系。
    """
    # 先清洗文本条件：空字符串按没填处理，避免前端空输入框误伤查询
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

    # 排好序后走统一分页
    query = query.order_by(ClassInfo.id.asc())
    return paginate(query, page, page_size)


def list_all_classes(db: Session):
    """查询全部未删除的班级（统计接口使用）"""
    return (
        db.query(ClassInfo)
        .filter(ClassInfo.is_deleted == 0)
        .order_by(ClassInfo.id.asc())
        .all()
    )


def create_class(db: Session, data: dict):
    """新增班级：data 是 {字段名: 值} 的字典"""
    class_info = ClassInfo(**data)
    db.add(class_info)
    db.commit()
    # refresh：重新从数据库读取，拿到自增ID、创建时间等数据库生成的值
    db.refresh(class_info)
    return class_info


def update_class(db: Session, class_info: ClassInfo, changes: dict):
    """更新班级：只修改 changes 里出现的字段"""
    for field_name, value in changes.items():
        setattr(class_info, field_name, value)
    db.commit()
    db.refresh(class_info)
    return class_info


def delete_class(db: Session, class_info: ClassInfo):
    """逻辑删除班级：不真正删除数据，只打上删除标记并记录删除时间"""
    class_info.is_deleted = 1
    class_info.deleted_at = datetime.now()
    db.commit()
