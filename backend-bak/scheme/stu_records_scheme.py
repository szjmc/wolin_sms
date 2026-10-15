from datetime import date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field,model_validator
from datetime import datetime

#枚举选择
class SalaryPeriod(str,Enum):
    year='年薪'
    month='月薪'

class EmploymentCreate(BaseModel):
    student_id: int = Field(gt=0, description="学生 ID")
    employment_open_date: date | None = Field(
        default=None,
        description="就业开放日期，格式 YYYY-MM-DD",
    )
    offer_date : date | None= Field(
        default=None,
        description="录取通知日期，格式 YYYY-MM-DD",
    )
    company_name: str | None = Field(min_length=1, max_length=150)
    employment_city: str | None = Field(default=None, max_length=100)
    position: str | None = Field(default=None, max_length=100)
    salary: Decimal = Field(gt=0, description="原始薪资金额")
    salary_period: SalaryPeriod

    @model_validator(mode="after")   #after用对象的方法访问，before用字典访问
    def check_offer_date(self) :
        if (self.offer_date is not None
                and self.employment_open_date is not None
                and  self.offer_date< self.employment_open_date):
            raise ValueError("Offer 日期不能早于就业开放日期")
        return self
#部分修改
class EmploymentUpdate(BaseModel):

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    employment_open_date: date | None = Field(default=None, description="就业开放日期")
    offer_date: date | None = Field(default=None, description="Offer 日期")
    company_name: str | None = Field(default=None, min_length=1, max_length=150, description="就业公司名称")
    employment_city: str | None = Field(default=None, max_length=100, description="就业城市")
    position: str | None = Field(default=None, max_length=100, description="就业岗位")
    salary_amount: Decimal | None = Field(default=None, ge=0, description="薪资金额，非负")
    salary_period: SalaryPeriod

    @model_validator(mode="after")
    def check_not_null(self, value):
        if value is None:
            raise ValueError("必填字段不能为 null")
        return value
#响应体
class EmploymentRecordOut(BaseModel):
    id: int
    student_id: int
    student_name_snapshot: str
    class_no_snapshot: str | None
    employment_open_date: date | None
    offer_date: date | None
    company_name: str
    employment_city: str | None
    position: str | None
    salary_amount: Decimal
    salary_period: SalaryPeriod
    annualized_salary: Decimal | None = Field(default=None,description="年薪等价值（服务端计算）：月薪×12 或 年薪本身")
    created_at: datetime
    updated_at: datetime