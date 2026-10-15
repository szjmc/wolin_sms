"""
学生过往经历模块的 Pydantic 模型
学生ID从 URL 路径 /students/{student_id}/past-experiences 中获取，所以新增请求体里不需要 student_id。
"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import SalaryPeriod, check_not_null


class PastExperienceCreate(BaseModel):
    """新增过往经历请求体"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    past_salary_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, description="过往薪资金额，非负", examples=[9000],
    )
    past_salary_period: SalaryPeriod | None = Field(default=None, description="过往薪资周期：MONTH=月薪，YEAR=年薪", examples=["MONTH"])
    work_years: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=5, decimal_places=2, description="工作年限，非负，可为小数", examples=[2.5],
    )
    graduation_date: date | None = Field(default=None, description="过往学历毕业日期（不是培训结课日期）", examples=["2022-06-30"])
    intended_city: str | None = Field(default=None, max_length=100, description="就业意向城市", examples=["杭州"])
    previous_position: str | None = Field(default=None, max_length=100, description="以往岗位", examples=["Python开发工程师"])

    @model_validator(mode="after")
    def check_salary_period(self):
        # 填写了薪资金额，就必须同时填写薪资周期（不能根据金额大小去猜是月薪还是年薪）
        if self.past_salary_amount is not None and self.past_salary_period is None:
            raise ValueError("填写过往薪资金额时必须同时填写薪资周期")
        return self


class PastExperienceUpdate(BaseModel):
    """修改过往经历请求体（PATCH）"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    past_salary_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2, description="过往薪资金额")
    past_salary_period: SalaryPeriod | None = Field(default=None, description="过往薪资周期：MONTH/YEAR")
    work_years: Decimal | None = Field(default=None, ge=0, max_digits=5, decimal_places=2, description="工作年限")
    graduation_date: date | None = Field(default=None, description="过往学历毕业日期")
    intended_city: str | None = Field(default=None, max_length=100, description="就业意向城市")
    previous_position: str | None = Field(default=None, max_length=100, description="以往岗位")

    @model_validator(mode="after")
    def check_required_fields(self):
        # work_years 在数据库中是必填字段，不能传 null
        check_not_null(self, ["work_years"])
        # 薪资金额和周期的搭配需要结合数据库原值判断，放在接口层检查
        return self


class PastExperienceRead(BaseModel):
    """过往经历响应数据"""

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
