"""学生过往经历模块的请求与响应模型。"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import SalaryPeriod, check_not_null


class PastExperienceCreate(BaseModel):
    """新增一条经历；student_id 来自 URL。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    past_salary_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
        description="过往薪资金额",
    )
    past_salary_period: SalaryPeriod | None = Field(
        default=None, description="薪资周期：MONTH/YEAR"
    )
    work_years: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=5,
        decimal_places=2,
        description="工作年限",
    )
    graduation_date: date | None = Field(
        default=None, description="过往学历毕业日期"
    )
    intended_city: str | None = Field(
        default=None, max_length=100, description="就业意向城市"
    )
    previous_position: str | None = Field(
        default=None, max_length=100, description="以往岗位"
    )

    @model_validator(mode="after")
    def check_salary_period(self):
        if self.past_salary_amount is not None and self.past_salary_period is None:
            raise ValueError("填写过往薪资金额时必须同时填写薪资周期")
        return self


class PastExperienceUpdate(BaseModel):
    """局部修改一条经历。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    past_salary_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    past_salary_period: SalaryPeriod | None = Field(default=None)
    work_years: Decimal | None = Field(
        default=None, ge=0, max_digits=5, decimal_places=2
    )
    graduation_date: date | None = Field(default=None)
    intended_city: str | None = Field(default=None, max_length=100)
    previous_position: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def check_required_fields(self):
        check_not_null(self, ["work_years"])
        # 薪资金额与周期必须和数据库原值合并后校验，由 API 层完成。
        return self


class PastExperienceRead(BaseModel):
    """过往经历响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    past_salary_amount: Decimal | None
    past_salary_period: SalaryPeriod | None
    work_years: Decimal
    graduation_date: date | None
    intended_city: str | None
    previous_position: str | None
    created_at: datetime
    updated_at: datetime
