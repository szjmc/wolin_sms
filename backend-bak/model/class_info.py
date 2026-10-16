"""
班级表 classes 的 ORM 模型
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class ClassInfo(Base):
    """
    班级表。
    说明：类名叫 ClassInfo 而不叫 Class，因为 class 是 Python 关键字，容易混淆。
    """

    # 数据库中的表名
    __tablename__ = "classes"

    # 主键：BIGINT 自增
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="班级主键ID")
    # 班级编号：业务编号，唯一（唯一索引对已逻辑删除的记录同样生效）
    class_no = Column(String(30), nullable=False, unique=True, comment="班级编号，如 WL2026-A")
    # 班级名称
    class_name = Column(String(100), nullable=False, comment="班级名称")
    # 开班日期
    start_date = Column(Date, nullable=False, comment="开班日期")
    # 班级结课日期：未结课时为空（和学生个人的培训结课日期是两个不同的字段）
    completion_date = Column(Date, nullable=True, comment="班级结课日期，未结课为空")
    # 班级状态：未开班 / 在读 / 已结课
    class_status = Column(String(20), nullable=False, default="在读", comment="班级状态：未开班/在读/已结课")

    # ========== 以下 4 个是所有表都有的公共字段 ==========
    # 逻辑删除标记：0=未删除，1=已删除。普通查询必须加条件 is_deleted == 0
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    # 逻辑删除时间：未删除时为空
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    # 创建时间：新增记录时自动填写当前时间
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    # 更新时间：新增时填写当前时间，之后每次修改自动刷新
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
