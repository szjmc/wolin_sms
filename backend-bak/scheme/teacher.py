"""
老师模块的 Pydantic 校验模型
============================
联系方式约定：phone 保存电话号码，contact_info 保存微信、邮箱等补充联系方式。
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import Gender, TeacherStatus, TeachingStatus, check_not_null

# [修改说明] 原代码：请求和响应使用 teacher_code、status、TeacherOut，与 ORM 和前端使用的 teacher_no、teacher_status 不一致，并缺少性别、专长、补充联系方式、教学年限等字段；修改原因：API 导入 TeacherRead 会失败，提交的字段也无法落到 teachers 表；修改为：保留 scheme/teacher.py 文件，按 backend 契约补齐 TeacherCreate、TeacherUpdate、TeacherRead 及完整校验。


class TeacherCreate(BaseModel):
    """新增老师请求体。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    teacher_no: str = Field(min_length=1, max_length=30, description="老师编号，全局唯一，创建后不可修改")
    name: str = Field(min_length=1, max_length=50, description="老师姓名")
    gender: Gender | None = Field(default=None, description="性别：男/女/其他")
    specialty: str | None = Field(default=None, max_length=100, description="教学专长")
    phone: str | None = Field(default=None, max_length=30, description="手机号")
    contact_info: str | None = Field(default=None, max_length=150, description="微信、邮箱等补充联系方式")
    teaching_years: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=5,
        decimal_places=2,
        description="教学年限，允许小数且不得为负",
    )
    teacher_status: TeacherStatus = Field(default="在职", description="老师状态：在职/离职")
    # [修改说明] 原代码：创建老师只接收 teacher_status；修改原因：排班业务需要单独维护授课可用性；修改为：新增受 TeachingStatus 枚举约束的 teaching_status，默认可授课，兼容旧请求。
    teaching_status: TeachingStatus = Field(default="可授课", description="授课状态：可授课/暂停授课")


class TeacherUpdate(BaseModel):
    """局部更新老师；老师编号不允许修改。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=50, description="老师姓名")
    gender: Gender | None = Field(default=None, description="性别：男/女/其他")
    specialty: str | None = Field(default=None, max_length=100, description="教学专长")
    phone: str | None = Field(default=None, max_length=30, description="手机号")
    contact_info: str | None = Field(default=None, max_length=150, description="补充联系方式")
    teaching_years: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=5,
        decimal_places=2,
        description="教学年限，不得为负",
    )
    teacher_status: TeacherStatus | None = Field(default=None, description="老师状态：在职/离职")
    # [修改说明] 原代码：更新老师不能调整授课可用性；修改原因：排班页需要暂停/恢复老师授课资格；修改为：PATCH 支持 teaching_status，并与其它非空业务字段一样拒绝显式 null。
    teaching_status: TeachingStatus | None = Field(default=None, description="授课状态：可授课/暂停授课")

    @model_validator(mode="after")
    def check_required_fields(self):
        check_not_null(self, ["name", "teaching_years", "teacher_status", "teaching_status"])
        return self


class TeacherRead(BaseModel):
    """老师响应数据。"""

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
    # [修改说明] 原代码：老师响应没有 teaching_status；修改原因：前端筛选可排班老师和全局排班表均依赖该字段；修改为：在 TeacherRead 中返回授课状态。
    teaching_status: str
    created_at: datetime
    updated_at: datetime
