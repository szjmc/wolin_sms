"""统计分析模块的响应模型。

[补全说明] backend-bak 原统计接口直接返回临时字典，缺少稳定的字段约束。本文件继续
使用小组现有 Pydantic v2 公共模型，补齐八个核心统计、工作台概览和班级概览 DTO。
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from scheme.class_info import ClassRead
from scheme.common import SalaryPeriod


class SystemOverview(BaseModel):
    """首页工作台使用的有效数据总量。"""

    student_total: int
    class_total: int
    teacher_total: int
    employment_total: int


class ClassStudentCount(BaseModel):
    """班级人数及性别分布。"""

    class_id: int
    class_no: str
    class_name: str
    total_students: int = Field(description="未删除学生总人数")
    male_count: int
    female_count: int
    other_count: int


class StudentFailureSummary(BaseModel):
    """多次不及格的学生。"""

    student_id: int
    student_no: str
    name: str
    class_id: int
    class_no: str
    class_name: str
    fail_count: int = Field(description="低于不及格线的有效成绩条数")


class ClassExamAverage(BaseModel):
    """某次考核中某个班级的平均分。"""

    class_id: int
    class_no: str
    class_name: str
    exam_no: int
    average_score: Decimal
    sample_count: int = Field(description="参与平均计算的有效成绩人次")


class TopSalaryItem(BaseModel):
    """按年薪等价值排序的一条就业记录。"""

    rank: int
    employment_record_id: int
    student_id: int
    student_name_snapshot: str
    class_no_snapshot: str
    education: str | None
    company_name: str
    employment_city: str | None
    position: str | None
    offer_date: date | None
    salary_amount: Decimal
    salary_period: SalaryPeriod
    annualized_salary: Decimal


class EmploymentDurationItem(BaseModel):
    """一条日期完整的就业记录对应的求职周期。"""

    employment_record_id: int
    student_id: int
    student_name_snapshot: str
    class_no_snapshot: str
    company_name: str
    employment_open_date: date
    offer_date: date
    duration_days: int


class ClassAverageDuration(BaseModel):
    """按就业记录班号快照分组的平均求职周期。"""

    class_no_snapshot: str
    record_count: int
    average_duration_days: Decimal


class ClassOverview(BaseModel):
    """班级详情页使用的档案、学情和就业聚合。"""

    class_info: ClassRead
    total_students: int
    male_count: int
    female_count: int
    other_count: int
    graded_students: int
    total_scores: int
    passing_scores: int
    pass_rate: Decimal | None
    average_score: Decimal | None
    qualified_students: int
    employed_students: int
