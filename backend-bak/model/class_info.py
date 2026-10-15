"""
班级及班级老师关系 ORM 模型
============================
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base

# [修改说明] 原代码：本文件同时简化定义 classes、teachers、students、scores 和 class_teacher_relations 五张表；修改原因：teachers/students/scores 已有各自模型，重复映射会在多路由启用后触发 SQLAlchemy 表冲突，且简化字段会覆盖完整结构；修改为：保留小组“班级与关系模型放在 class_info.py”的结构，仅维护 ClassInfo 和 ClassTeacherRelation，其他实体由各自模块负责。


class ClassInfo(Base):
    """班级实体模型，映射 classes 表。"""

    __tablename__ = "classes"

    # [修改说明] 原代码：classes 主键固定为 Integer、删除标记也使用 Integer；修改原因：MySQL 初始化脚本统一为 BIGINT/TINYINT，ORM 自动建表时会产生不同结构；修改为：MySQL 使用 BIGINT/TINYINT，SQLite 测试分别映射为可自增的 INTEGER 和普通 INTEGER。
    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="班级主键ID",
    )
    class_no = Column(String(30), unique=True, nullable=False, comment="班级编号")
    class_name = Column(String(100), nullable=False, comment="班级名称")
    start_date = Column(Date, nullable=False, comment="开班日期")
    completion_date = Column(Date, nullable=True, comment="班级结课日期")
    class_status = Column(
        String(20),
        nullable=False,
        default="在读",
        server_default="在读",
        comment="班级状态：未开班/在读/已结课",
    )

    # [修改说明] 原代码：班级表没有逻辑删除和创建/更新时间字段；修改原因：原删除接口只能物理删除，无法保留历史，也不能与 backend 的统一查询规则对齐；修改为：增加 is_deleted、deleted_at、created_at、updated_at 四个公共字段。
    is_deleted = Column(
        TINYINT().with_variant(Integer, "sqlite"),
        nullable=False,
        default=0,
        server_default="0",
        comment="逻辑删除：0=未删除，1=已删除",
    )
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )


class ClassTeacherRelation(Base):
    """班级与老师的关系模型。"""

    __tablename__ = "class_teacher_relations"

    # [修改说明] 原代码：关系表三个 ID 都是 Integer 且没有数据库外键；修改原因：与 MySQL BIGINT 主键体系和 init_mysql.sql 外键定义不一致，ORM 自动建表无法提供关联完整性保护；修改为：主键保持 SQLite 自增兼容，生产使用 BIGINT，并补回 classes/teachers 的 RESTRICT 外键。
    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="关系记录主键ID",
    )
    class_id = Column(
        BigInteger,
        ForeignKey("classes.id", ondelete="RESTRICT"),
        nullable=False,
        comment="班级ID",
    )
    teacher_id = Column(
        BigInteger,
        ForeignKey("teachers.id", ondelete="RESTRICT"),
        nullable=False,
        comment="老师ID",
    )
    relation_type = Column(
        String(30),
        nullable=False,
        default="授课老师",
        server_default="授课老师",
        comment="关系类型：班主任/授课老师",
    )

    # [修改说明] 原代码：关系表只有 is_deleted，没有删除时间和审计时间；修改原因：解除排班必须逻辑删除并保留历史，班级删除保护也只检查有效关系；修改为：补齐统一的逻辑删除与时间字段。
    is_deleted = Column(
        TINYINT().with_variant(Integer, "sqlite"),
        nullable=False,
        default=0,
        server_default="0",
        comment="逻辑删除：0=未删除，1=已删除",
    )
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )
