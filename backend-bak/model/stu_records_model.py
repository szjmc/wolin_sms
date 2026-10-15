"""就业记录 ORM 模型。

继续保留小组原 ``model/stu_records_model.py`` 和 ``EmploymentRecord`` 类名；表结构
在原有就业字段上补入不可变的就业前经历快照，以支撑岗位、薪资成长对比。
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


# [修改说明] 原代码：主键固定 BIGINT、class_no_snapshot 可空，且声明了 Student 端不存在的 back_populates 关系；修改原因：SQLite 无法为 BIGINT 主键自增、快照可能缺失且 mapper 初始化会报错；修改为：保留 BIGINT 的 MySQL 结构并为 SQLite 使用 INTEGER，班号快照改为必填，就业查询统一由 DAO 显式联表，不再依赖错误关系。
class EmploymentRecord(Base):
    """学生的一次就业经历；一名学生可保存多条历史记录。"""

    __tablename__ = "employment_records"
    __table_args__ = (
        Index("idx_emp_student_deleted", "student_id", "is_deleted"),
        {"comment": "就业记录表", "mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="就业记录主键ID",
    )
    student_id = Column(
        BigInteger,
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        comment="学生ID",
    )
    student_name_snapshot = Column(
        String(50), nullable=False, comment="创建记录时的学生姓名快照"
    )
    class_no_snapshot = Column(
        String(30), nullable=False, comment="创建记录时的班级编号快照"
    )
    employment_open_date = Column(Date, nullable=True, comment="就业开放日期")
    offer_date = Column(Date, nullable=True, comment="Offer日期")
    company_name = Column(String(150), nullable=False, comment="就业公司名称")
    employment_city = Column(String(100), nullable=True, comment="就业城市")
    position = Column(String(100), nullable=True, comment="就业岗位")
    salary_amount = Column(
        Numeric(12, 2), nullable=False, comment="薪资金额（原始值）"
    )
    salary_period = Column(
        Enum("MONTH", "YEAR", name="salary_period_enum"),
        nullable=False,
        comment="薪资周期：MONTH=月薪，YEAR=年薪",
    )

    # [修改说明] 原代码：就业记录仅保存本次就业薪资；修改原因：直接读取学生当前过往经历会让历史对比随档案修改而变化；修改为：新增四个创建时只复制一次的就业前快照字段，后续只有显式 PATCH 才更新。
    past_salary_amount = Column(
        Numeric(12, 2), nullable=True, comment="创建记录时的过往薪资金额快照"
    )
    past_salary_period = Column(
        Enum("MONTH", "YEAR", name="past_salary_period_enum"),
        nullable=True,
        comment="过往薪资周期快照：MONTH/YEAR",
    )
    previous_position = Column(
        String(100), nullable=True, comment="创建记录时的以往岗位快照"
    )
    past_graduation_date = Column(
        Date, nullable=True, comment="创建记录时的原学历毕业日期快照"
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
