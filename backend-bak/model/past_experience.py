"""学生过往经历表 ORM 模型。

一名学生可以保存多条相互独立的历史经历。
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
    Numeric,
    String,
)
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class StudentPastExperience(Base):
    """学生就业前的岗位、薪资和学历经历。"""

    __tablename__ = "student_past_experiences"
    __table_args__ = (
        Index("idx_past_exp_student_deleted", "student_id", "is_deleted"),
        {
            "comment": "学生过往经历表",
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
        },
    )

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="过往经历主键ID",
    )
    student_id = Column(
        BigInteger,
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        comment="学生ID",
    )
    past_salary_amount = Column(
        Numeric(12, 2), nullable=True, comment="过往薪资金额"
    )
    past_salary_period = Column(
        Enum("MONTH", "YEAR", name="past_salary_period_enum"),
        nullable=True,
        comment="过往薪资周期：MONTH=月薪，YEAR=年薪",
    )
    work_years = Column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        server_default="0",
        comment="工作年限",
    )
    graduation_date = Column(
        Date, nullable=True, comment="过往学历毕业日期"
    )
    intended_city = Column(String(100), nullable=True, comment="就业意向城市")
    previous_position = Column(String(100), nullable=True, comment="以往岗位")

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
