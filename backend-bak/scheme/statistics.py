"""
统计分析模块的响应模型
统计结果尽量返回有业务含义的字段，而不是只返回一个匿名数字。
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from scheme.common import SalaryPeriod


class ClassStudentCount(BaseModel):
    """班级人数统计"""

    class_id: int
    class_no: str
    class_name: str
    total_students: int = Field(description="未删除学生总人数（男 + 女 + 其他）")
    male_count: int = Field(description="男生人数")
    female_count: int = Field(description="女生人数")
    other_count: int = Field(description="其他性别人数")


class StudentFailureSummary(BaseModel):
    """多次不及格的学生（前端重点帮扶预警卡片用）"""

    student_id: int
    student_no: str
    name: str
    class_id: int
    class_no: str = Field(description="班级编号")
    class_name: str = Field(description="班级名称，前端预警卡片直接展示，不用再查一次班级")
    fail_count: int = Field(description="低于不及格线的有效成绩条数")


class ClassExamAverage(BaseModel):
    """某次考核某个班级的平均分"""

    class_id: int
    class_no: str
    class_name: str
    exam_no: int
    average_score: Decimal = Field(description="平均分，保留两位小数；有分组就一定有成绩，所以不会为空")
    sample_count: int = Field(description="样本量：参与平均的有效成绩条数（人次），前端展示“分（N人次）”")


class TopSalaryItem(BaseModel):
    """薪资排行中的一条记录"""

    rank: int = Field(description="名次，从 1 开始；年薪等价值相同时按记录ID先后排")
    employment_record_id: int
    student_id: int
    student_name_snapshot: str
    class_no_snapshot: str
    education: str | None = Field(description="学生学历（从学生档案带出，档案没填就是空）")
    company_name: str
    employment_city: str | None
    position: str | None
    offer_date: date | None
    salary_amount: Decimal = Field(description="原始薪资金额")
    salary_period: SalaryPeriod = Field(description="原始薪资周期")
    annualized_salary: Decimal = Field(description="年薪等价值（排序依据）")


class EmploymentDurationItem(BaseModel):
    """单条就业记录的就业时长"""

    employment_record_id: int
    student_id: int
    student_name_snapshot: str
    class_no_snapshot: str
    company_name: str
    employment_open_date: date
    offer_date: date
    duration_days: int = Field(description="就业时长（自然日）= Offer 日期 - 就业开放日期")


class ClassAverageDuration(BaseModel):
    """班级平均就业时长（按就业记录中的班级快照统计）"""

    class_no_snapshot: str
    record_count: int = Field(description="参与统计的就业记录条数（两个日期都有值的记录）")
    average_duration_days: Decimal = Field(description="平均就业时长（天），保留两位小数；有分组就一定有值")
