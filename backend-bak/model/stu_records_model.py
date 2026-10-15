from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import BigInteger, Column, Date, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base

   #就业记录表
class EmploymentRecord(Base):


    __tablename__ = "employment_records"


    # 主键：BIGINT 自增
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="就业记录主键ID")
    # 学生ID：外键关联 students.id（不唯一，一个学生可以有多条记录）
    student_id = Column(BigInteger, ForeignKey("students.id"), nullable=False, comment="学生ID")
    # 学生姓名快照：新增时由服务端从学生档案复制
    student_name_snapshot = Column(String(50), nullable=False, comment="学生姓名快照")
    # 班级编号快照：新增时由服务端从学生当前班级复制
    class_no_snapshot = Column(String(30), nullable=True, comment="班级编号快照")
    # 就业开放日期（开始就业服务的日期）
    employment_open_date = Column(Date, nullable=True, comment="就业开放日期")
    # 拿到 Offer 的日期
    offer_date = Column(Date, nullable=True, comment="Offer 日期")
    # 就业公司名称
    company_name = Column(String(150), nullable=False, comment="就业公司名称")
    # 就业城市
    employment_city = Column(String(100), nullable=True, comment="就业城市")
    # 就业岗位
    position = Column(String(100), nullable=True, comment="就业岗位")
    # 薪资金额（原始值）：非负
    salary_amount = Column(Numeric(12, 2), nullable=False, comment="薪资金额（原始值）")
    # 薪资周期：MONTH=月薪，YEAR=年薪
    salary_period = Column(
        Enum("MONTH", "YEAR", name="salary_period_enum"),
        nullable=False,
        comment="薪资周期：MONTH=月薪，YEAR=年薪",
    )
    student = relationship(
        "Student",
        back_populates="employment_records"
    )

    # 公共字段：逻辑删除
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
