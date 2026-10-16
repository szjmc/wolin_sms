"""
就业记录模块的 Pydantic 模型

注意：
1. student_name_snapshot / class_no_snapshot（快照字段）由服务端自动填写，请求体里没有这两个字段。
2. annualized_salary（年薪等价值）是服务端计算出来的，不存数据库：
   MONTH（月薪）→ salary_amount × 12；YEAR（年薪）→ salary_amount
3. 必填和选填的分界：
   - 新增时必填：student_id、company_name、salary_amount、salary_period（数据库 NOT NULL）
   - 可选：employment_open_date、offer_date、employment_city、position
     （记录可以先开放就业服务再慢慢补 Offer，所以日期和城市岗位允许为空）
"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import SalaryPeriod, check_not_null


class EmploymentCreate(BaseModel):
    """新增就业记录请求体（每次新增都是一条新记录，不会覆盖该学生已有的就业记录）"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    student_id: int = Field(gt=0, description="学生ID（必须是未删除的学生）", examples=[1])
    employment_open_date: date | None = Field(default=None, description="就业开放日期（开始就业服务的日期）", examples=["2026-01-10"])
    offer_date: date | None = Field(default=None, description="拿到 Offer 的日期，不能早于就业开放日期", examples=["2026-02-15"])
    company_name: str = Field(min_length=1, max_length=150, description="就业公司名称", examples=["示例科技有限公司"])
    employment_city: str | None = Field(default=None, max_length=100, description="就业城市", examples=["杭州"])
    position: str | None = Field(default=None, max_length=100, description="就业岗位", examples=["后端开发工程师"])
    salary_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2, description="薪资金额（原始值），非负", examples=[15000])
    salary_period: SalaryPeriod = Field(description="薪资周期：MONTH=月薪，YEAR=年薪", examples=["MONTH"])

    @model_validator(mode="after")
    def check_dates(self):
        # 规则 0：学生必须结课后才能新增就业信息（学生结课日期在数据库里，接口层校验）
        # 规则 1：就业还没开放就不能有 Offer（先开放再拿 Offer，这是业务顺序）
        if self.offer_date is not None and self.employment_open_date is None:
            raise ValueError("就业尚未开放，填写 Offer 日期之前请先填写就业开放日期")
        # 规则 2：两个日期都填写时，Offer 日期不能早于就业开放日期
        if self.employment_open_date is not None and self.offer_date is not None:
            if self.offer_date < self.employment_open_date:
                raise ValueError("Offer 日期不能早于就业开放日期")
        return self


class EmploymentUpdate(BaseModel):
    """修改就业记录请求体（PATCH，只修改这一条记录，不允许修改所属学生和快照字段）"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    employment_open_date: date | None = Field(default=None, description="就业开放日期")
    offer_date: date | None = Field(default=None, description="Offer 日期")
    company_name: str | None = Field(default=None, min_length=1, max_length=150, description="就业公司名称")
    employment_city: str | None = Field(default=None, max_length=100, description="就业城市")
    position: str | None = Field(default=None, max_length=100, description="就业岗位")
    salary_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2, description="薪资金额，非负")
    salary_period: SalaryPeriod | None = Field(default=None, description="薪资周期：MONTH/YEAR")

    @model_validator(mode="after")
    def check_required_fields(self):
        # 数据库必填字段：PATCH 时可以不传，但不能传 null
        check_not_null(self, ["company_name", "salary_amount", "salary_period"])
        # 两个日期的先后顺序需要结合数据库原值判断，放在接口层检查
        return self


class EmploymentRead(BaseModel):
    """
    就业记录响应数据。
    注意：两个快照和年薪等价值都是必填（没有 | None），
    因为服务端新增时一定会填快照，薪资必填所以年薪等价值一定能算出来。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    student_name_snapshot: str
    class_no_snapshot: str
    employment_open_date: date | None
    offer_date: date | None
    company_name: str
    employment_city: str | None
    position: str | None
    salary_amount: Decimal
    salary_period: SalaryPeriod
    offer_status: str = Field(description="Offer 状态：待处理/已接受/已拒绝；一名学生多个 Offer 选中一条其余自动拒绝")
    annualized_salary: Decimal = Field(
        default=Decimal("0"),
        description="年薪等价值（服务端计算后填入）：月薪×12 或 年薪本身",
    )
    created_at: datetime
    updated_at: datetime
