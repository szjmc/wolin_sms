"""就业记录模块的请求与响应模型。

保留小组原 ``stu_records_scheme.py`` 文件名，对齐统一分页响应、MONTH/YEAR 薪资
口径，并补入就业前经历快照及薪资对比 DTO。
"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import SalaryPeriod, check_not_null


# [修改说明] 原代码：在本文件重复定义值为“年薪/月薪”的枚举，新增字段又命名为 salary，导致 MONTH/YEAR 请求及 salary_amount 均无法校验；修改原因：与建库 SQL、完整后端及前端契约不一致；修改为：复用公共 SalaryPeriod，恢复 salary_amount，并使用 Pydantic v2 约束声明。
class EmploymentRecordCreate(BaseModel):
    """新增一条就业记录；姓名与班号快照由服务端根据 student_id 填入。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    student_id: int = Field(gt=0, description="学生 ID")
    employment_open_date: date | None = Field(default=None, description="就业开放日期")
    offer_date: date | None = Field(default=None, description="Offer 日期")
    company_name: str = Field(min_length=1, max_length=150, description="就业公司")
    employment_city: str | None = Field(default=None, max_length=100, description="就业城市")
    position: str | None = Field(default=None, max_length=100, description="就业岗位")
    salary_amount: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
        description="原始薪资金额",
    )
    salary_period: SalaryPeriod = Field(description="薪资周期：MONTH/YEAR")

    # 客户端不传这些字段时，接口会从该学生最近一条有效过往经历复制；显式 null
    # 表示本条记录不采用对应历史数据。
    past_salary_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    past_salary_period: SalaryPeriod | None = Field(default=None)
    previous_position: str | None = Field(default=None, max_length=100)
    past_graduation_date: date | None = Field(default=None)

    @model_validator(mode="after")
    def validate_business_fields(self):
        if self.offer_date is not None and self.employment_open_date is None:
            raise ValueError("就业尚未开放，填写 Offer 日期之前请先填写就业开放日期")
        if (
            self.employment_open_date is not None
            and self.offer_date is not None
            and self.offer_date < self.employment_open_date
        ):
            raise ValueError("Offer 日期不能早于就业开放日期")
        # 以往薪资与周期需先分别和最近一条过往经历合并，再由 API 校验组合。
        if self.past_graduation_date is not None and self.past_graduation_date > date.today():
            raise ValueError("学历毕业日期不能晚于今天")
        return self


# [修改说明] 原代码：PATCH 把 salary_period 错误设为必传，validator 仍按 Pydantic v1 的 values 参数取值，并把可空字段全部当成必填；修改原因：局部更新会校验报错或错误覆盖字段；修改为：全部字段可省略，只禁止三个数据库必填字段显式传 null，跨字段规则在与数据库原值合并后由 API 校验。
class EmploymentRecordUpdate(BaseModel):
    """局部更新就业记录；未出现的字段保持原值。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    employment_open_date: date | None = Field(default=None)
    offer_date: date | None = Field(default=None)
    company_name: str | None = Field(default=None, min_length=1, max_length=150)
    employment_city: str | None = Field(default=None, max_length=100)
    position: str | None = Field(default=None, max_length=100)
    salary_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    salary_period: SalaryPeriod | None = Field(default=None)
    past_salary_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    past_salary_period: SalaryPeriod | None = Field(default=None)
    previous_position: str | None = Field(default=None, max_length=100)
    past_graduation_date: date | None = Field(default=None)

    @model_validator(mode="after")
    def validate_patch_fields(self):
        check_not_null(self, ["company_name", "salary_amount", "salary_period"])
        if (
            self.employment_open_date is not None
            and self.offer_date is not None
            and self.offer_date < self.employment_open_date
        ):
            raise ValueError("Offer 日期不能早于就业开放日期")
        if self.past_graduation_date is not None and self.past_graduation_date > date.today():
            raise ValueError("学历毕业日期不能晚于今天")
        return self


class EmploymentRecordOut(BaseModel):
    """就业记录响应；派生字段不落库。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    student_no: str | None = None
    student_name_snapshot: str
    class_id: int | None = None
    class_no_snapshot: str
    employment_open_date: date | None
    offer_date: date | None
    company_name: str
    employment_city: str | None
    position: str | None
    salary_amount: Decimal
    salary_period: SalaryPeriod
    annualized_salary: Decimal
    past_salary_amount: Decimal | None
    past_salary_period: SalaryPeriod | None
    previous_position: str | None
    past_graduation_date: date | None
    graduation_years: int | None
    created_at: datetime
    updated_at: datetime


# 保留小组 API 已使用的旧导入名，并兼容完整后端的简写命名。
EmploymentCreate = EmploymentRecordCreate
EmploymentUpdate = EmploymentRecordUpdate
EmploymentRead = EmploymentRecordOut


class EmploymentOptions(BaseModel):
    """有效就业记录中可供筛选的城市和岗位。"""

    cities: list[str]
    positions: list[str]


class SalaryComparisonOut(BaseModel):
    """同一条就业记录中培训前后岗位及薪资的统一口径对比。"""

    employment_record_id: int
    student_id: int
    student_name_snapshot: str
    previous_position: str | None
    position: str | None
    past_salary_amount: Decimal | None
    past_salary_period: SalaryPeriod | None
    salary_amount: Decimal
    salary_period: SalaryPeriod
    past_annualized_salary: Decimal | None
    annualized_salary: Decimal
    monthly_before: Decimal | None
    monthly_after: Decimal
    annual_increase: Decimal | None
    increase_percent: Decimal | None
    comparison_available: bool
