"""学生表 ORM 模型。

保留小组既有 ``model/students_model.py`` 文件和 ``StudentDB`` 导入名；表结构、必填约束
及审计字段对齐完整后端和建库 SQL。
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


# [修改说明] 原代码：StudentDB 使用可空 class_id/birth_date/gender、Boolean 删除标记以及 create_time/update_time，字段长度也与建库 SQL 不一致；修改原因：会接受不完整学生档案，且连接既有 MySQL 表时找不到时间字段；修改为：在原文件中统一为正式 students 表结构，并将类命名为 Student 以供成绩和就业关系模块复用，继续提供 StudentDB 兼容别名。
class Student(Base):
    """学生实体；年龄不落库，由 birth_date 动态计算。"""

    __tablename__ = "students"
    __table_args__ = (
        Index("idx_students_class_deleted", "class_id", "is_deleted"),
        Index("idx_students_name_deleted", "name", "is_deleted"),
        Index("idx_students_birth_deleted", "birth_date", "is_deleted"),
        {"comment": "学生表", "mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    # MySQL 保持 BIGINT；SQLite 测试使用 INTEGER PRIMARY KEY 才能自动生成主键。
    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="学生主键ID",
    )
    student_no = Column(
        String(30), nullable=False, unique=True, index=True, comment="学生编号"
    )
    # [修改说明] 原代码：class_id 只靠 API 校验，没有声明数据库外键；修改原因：ORM 自动建表结果与 init_mysql.sql 不一致，绕过 API 写入时也缺少关联完整性保护；修改为：继续保留 API 的友好 404 校验，同时补回指向 classes.id 的 RESTRICT 外键。
    class_id = Column(
        BigInteger,
        ForeignKey("classes.id", ondelete="RESTRICT"),
        nullable=False,
        comment="所属培训班级ID",
    )
    name = Column(String(50), nullable=False, comment="学生姓名")
    hometown = Column(String(100), nullable=True, comment="籍贯")
    graduate_school = Column(String(150), nullable=True, comment="原毕业院校")
    major = Column(String(100), nullable=True, comment="原专业")
    training_enrollment_date = Column(
        Date, nullable=True, comment="培训入学日期（培训机构）"
    )
    training_graduation_date = Column(
        Date, nullable=True, comment="培训毕业/结课日期（培训机构）"
    )
    education = Column(String(30), nullable=True, comment="学历")
    consultant_no = Column(
        String(30), nullable=True, comment="顾问编号（扩展预留，不建外键）"
    )
    birth_date = Column(
        Date, nullable=False, comment="出生日期（年龄由此动态计算）"
    )
    gender = Column(
        Enum("男", "女", "其他", name="student_gender_enum"),
        nullable=False,
        comment="性别：男/女/其他",
    )

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


# 保留小组代码及已接入班级 DAO 使用的原类名。
StudentDB = Student
