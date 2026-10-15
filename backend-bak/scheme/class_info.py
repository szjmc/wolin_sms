"""
班级模块的 Pydantic 校验模型
============================
"""
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import ClassStatus, check_not_null
from scheme.teacher import TeacherRead

# [修改说明] 原代码：start_date、class_status 可空且使用任意字符串，缺少日期先后校验、PATCH 必填字段保护和 ClassRead；修改原因：会写入不完整班级、接受非法状态，并且无法声明统一响应模型；修改为：按 backend 契约补齐 Create/Update/Read，使用枚举、去空格、日期校验和显式 null 校验。


PositiveId = Annotated[int, Field(gt=0)]


# [修改说明] 原代码：上一阶段为避免未校验排班而暂时从 ClassCreate 移除了老师 ID；修改原因：关系模块现已具备完整冲突校验，且前端建班表单要求班级与教学团队一次原子创建；修改为：恢复兼容的单个 teacher_id，并新增 head_teacher_id、teacher_ids，多条关系由 API 校验后在同一事务写入。
class ClassCreate(BaseModel):
    """新增班级请求体。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    class_no: str = Field(min_length=1, max_length=30, description="班级编号，全局唯一，创建后不可修改")
    class_name: str = Field(min_length=1, max_length=100, description="班级名称")
    start_date: date = Field(description="开班日期")
    completion_date: date | None = Field(default=None, description="班级结课日期，未结课可不填")
    class_status: ClassStatus = Field(default="在读", description="班级状态：未开班/在读/已结课")
    head_teacher_id: PositiveId | None = Field(default=None, description="建班时指定的班主任 ID")
    teacher_ids: list[PositiveId] = Field(default_factory=list, description="建班时指定的任课老师 ID 列表")
    teacher_id: PositiveId | None = Field(default=None, description="兼容小组原请求的单个任课老师 ID")

    @model_validator(mode="after")
    def check_dates_and_assignments(self):
        if self.completion_date is not None and self.completion_date < self.start_date:
            raise ValueError("班级结课日期不能早于开班日期")
        lecturer_ids = [*self.teacher_ids]
        if self.teacher_id is not None:
            lecturer_ids.append(self.teacher_id)
        if len(lecturer_ids) != len(set(lecturer_ids)):
            raise ValueError("任课老师 ID 不能重复")
        if self.head_teacher_id is not None and self.head_teacher_id in lecturer_ids:
            raise ValueError("班主任和授课老师不能是同一人")
        return self


class ClassUpdate(BaseModel):
    """更新班级请求体；班级编号不允许修改。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    class_name: str | None = Field(default=None, min_length=1, max_length=100, description="班级名称")
    start_date: date | None = Field(default=None, description="开班日期")
    completion_date: date | None = Field(default=None, description="班级结课日期；显式 null 表示清空")
    class_status: ClassStatus | None = Field(default=None, description="班级状态：未开班/在读/已结课")

    @model_validator(mode="after")
    def check_required_fields(self):
        check_not_null(self, ["class_name", "start_date", "class_status"])
        return self


class ClassRead(BaseModel):
    """班级响应数据。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    class_no: str
    class_name: str
    start_date: date
    completion_date: date | None
    class_status: str
    # [修改说明] 原代码：班级响应只有 classes 表字段；修改原因：班级列表和详情页需要直接显示人数、班主任和任课老师；修改为：追加带默认值的聚合字段，保持旧有基础字段兼容。
    total_students: int = 0
    head_teacher: TeacherRead | None = None
    teachers: list[TeacherRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
