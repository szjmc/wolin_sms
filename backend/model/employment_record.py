"""
就业记录表 employment_records 的 ORM 模型

重要约定：
1. 一名学生可以有多条就业记录（保留每段就业历史，新增不覆盖旧记录），
   所以 student_id 上不能建唯一索引。
2. 薪资同时保存"原始金额 salary_amount"和"薪资周期 salary_period"，
   排名时再换算成年薪等价值（月薪 × 12），不修改原始金额。
3. student_name_snapshot / class_no_snapshot 是新增记录时从学生档案复制的"快照"，
   以后学生改名或转班，历史就业记录里的快照保持不变。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class EmploymentRecord(Base):
    """就业记录表"""

    __tablename__ = "employment_records"

    # 主键：BIGINT 自增
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="就业记录主键ID")
    # 学生ID：外键关联 students.id（不唯一，一个学生可以有多条记录）
    student_id = Column(BigInteger, ForeignKey("students.id"), nullable=False, comment="学生ID")
    # 学生姓名快照：新增时由服务端从学生档案复制
    student_name_snapshot = Column(String(50), nullable=False, comment="学生姓名快照")
    # 班级编号快照：必填。新增时服务端必须从学生当前班级复制填入，不允许为空。
    # 学生一定有所属班级（建档时必填，删班级前会先检查还有没有学生），所以快照一定能取到。
    class_no_snapshot = Column(String(30), nullable=False, comment="班级编号快照")
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

    # ========== 公共字段：逻辑删除 + 时间戳 ==========
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
