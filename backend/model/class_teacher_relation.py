"""
班级老师关系表 class_teacher_relations 的 ORM 模型
用来区分"班主任"和"授课老师"。解除关系时只做逻辑删除，保留历史记录。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class ClassTeacherRelation(Base):
    """班级老师关系表"""

    __tablename__ = "class_teacher_relations"

    # 主键：BIGINT 自增
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="关系记录主键ID")
    # 班级ID：外键关联 classes.id
    class_id = Column(BigInteger, ForeignKey("classes.id"), nullable=False, comment="班级ID")
    # 老师ID：外键关联 teachers.id
    teacher_id = Column(BigInteger, ForeignKey("teachers.id"), nullable=False, comment="老师ID")
    # 关系类型：班主任 / 授课老师
    relation_type = Column(String(30), nullable=False, default="授课老师", comment="关系类型：班主任/授课老师")

    # ========== 公共字段：逻辑删除 + 时间戳 ==========
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
