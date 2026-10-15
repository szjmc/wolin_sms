"""班级—老师关系（排班）模块的请求与响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from scheme.common import RelationType
from scheme.teacher import TeacherRead


class ClassTeacherCreate(BaseModel):
    """新增排班关系请求体。"""

    model_config = ConfigDict(use_enum_values=True)

    relation_type: RelationType = Field(default="授课老师", description="关系类型：班主任/授课老师")


class ClassTeacherRead(BaseModel):
    """关系记录响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    teacher_id: int
    relation_type: str
    created_at: datetime
    updated_at: datetime


class ClassTeacherOverview(BaseModel):
    """班级或老师详情中的排班摘要。"""

    id: int
    class_id: int
    class_no: str
    class_name: str
    class_status: str
    teacher_id: int
    relation_type: str
    teacher: TeacherRead
    created_at: datetime
    updated_at: datetime


class ClassTeacherRelationOverview(BaseModel):
    """排班管理页使用的扁平关系 DTO。"""

    id: int
    class_id: int
    class_no: str
    class_name: str
    class_status: str
    teacher_id: int
    teacher_no: str
    teacher_name: str
    specialty: str | None
    phone: str | None
    teacher_status: str
    teaching_status: str
    relation_type: str
    created_at: datetime
    updated_at: datetime


class TeacherDetailRead(TeacherRead):
    """老师详情；在基础信息外附带当前有效班级关系。"""

    relations: list[ClassTeacherRelationOverview] = Field(default_factory=list)
