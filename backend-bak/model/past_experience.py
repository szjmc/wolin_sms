"""
学生过往经历表 student_past_experiences 的 ORM 模型
一名学生可以有多条过往经历（通过 student_id 关联 students.id）。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class StudentPastExperience(Base):
    """学生过往经历表"""

    __tablename__ = "student_past_experiences"

    # 主键：BIGINT 自增
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="过往经历主键ID")
    # 学生ID：外键关联 students.id
    student_id = Column(BigInteger, ForeignKey("students.id"), nullable=False, comment="学生ID")
    # 过往薪资金额：非负，可为空
    past_salary_amount = Column(Numeric(12, 2), nullable=True, comment="过往薪资金额")
    # 过往薪资周期：MONTH=月薪，YEAR=年薪（不能根据金额大小去猜）
    past_salary_period = Column(
        Enum("MONTH", "YEAR", name="past_salary_period_enum"),
        nullable=True,
        comment="过往薪资周期：MONTH=月薪，YEAR=年薪",
    )
    # 工作年限：非负，可为小数
    work_years = Column(Numeric(5, 2), nullable=False, default=0, server_default="0", comment="工作年限")
    # 过往学历毕业日期（不是培训结课日期）
    graduation_date = Column(Date, nullable=True, comment="过往学历毕业日期")
    # 就业意向城市
    intended_city = Column(String(100), nullable=True, comment="就业意向城市")
    # 以往岗位
    previous_position = Column(String(100), nullable=True, comment="以往岗位")

    # ========== 公共字段：逻辑删除 + 时间戳 ==========
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
