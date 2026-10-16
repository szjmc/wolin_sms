"""
老师模块的 Pydantic 模型
联系方式约定：phone 只保存电话号码；contact_info 保存微信、邮箱等补充联系方式。
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import Gender, TeacherStatus, TeachingStatus, check_not_null


class TeacherCreate(BaseModel):
    """新增老师请求体"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    teacher_no: str = Field(min_length=1, max_length=30, description="老师编号，全局唯一，创建后不可修改", examples=["T001"])
    name: str = Field(min_length=1, max_length=50, description="老师姓名", examples=["李明"])
    gender: Gender | None = Field(default=None, description="性别：男/女/其他，可不填")
    specialty: str | None = Field(default=None, max_length=100, description="教学专长", examples=["Python 后端开发"])
    phone: str | None = Field(default=None, max_length=30, description="手机号（只保存电话号码）", examples=["13800000000"])
    contact_info: str | None = Field(default=None, max_length=150, description="补充联系方式，如微信、邮箱，可为空", examples=["微信：liming_wl"])
    teaching_years: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=5, decimal_places=2,
        description="教学年限，允许小数（如 5.5），不得为负", examples=[5.5],
    )
    teacher_status: TeacherStatus = Field(default="在职", description="老师状态：在职/离职")
    teaching_status: TeachingStatus = Field(default="可授课", description="授课状态：可授课/暂停授课")


class TeacherUpdate(BaseModel):
    """更新老师请求体（PATCH，老师编号不允许修改）"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=50, description="老师姓名")
    gender: Gender | None = Field(default=None, description="性别：男/女/其他")
    specialty: str | None = Field(default=None, max_length=100, description="教学专长")
    phone: str | None = Field(default=None, max_length=30, description="手机号")
    contact_info: str | None = Field(default=None, max_length=150, description="补充联系方式")
    teaching_years: Decimal | None = Field(default=None, ge=0, max_digits=5, decimal_places=2, description="教学年限，不得为负")
    teacher_status: TeacherStatus | None = Field(default=None, description="老师状态：在职/离职")
    teaching_status: TeachingStatus | None = Field(default=None, description="授课状态：可授课/暂停授课")

    @model_validator(mode="after")
    def check_required_fields(self):
        # 数据库必填字段：PATCH 时可以不传，但不能传 null
        check_not_null(self, ["name", "teaching_years", "teacher_status"])
        return self


class TeacherRead(BaseModel):
    """老师响应数据"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_no: str
    name: str
    gender: Gender | None
    specialty: str | None
    phone: str | None
    contact_info: str | None
    teaching_years: Decimal
    teacher_status: str
    teaching_status: str
    created_at: datetime
    updated_at: datetime
