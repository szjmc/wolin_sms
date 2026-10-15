"""
班级老师关系模块的 Pydantic 模型
class_id 和 teacher_id 都从 URL 路径中获取，请求体里只需要传关系类型。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from scheme.common import RelationType
from scheme.teacher import TeacherRead


class ClassTeacherRelationCreate(BaseModel):
    """建立班级老师关系请求体"""

    model_config = ConfigDict(use_enum_values=True)

    relation_type: RelationType = Field(default="授课老师", description="关系类型：班主任/授课老师")


class ClassTeacherRelationRead(BaseModel):
    """班级老师关系响应数据"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    teacher_id: int
    relation_type: str
    created_at: datetime


class ClassTeacherItem(BaseModel):
    """班级老师列表中的一行：关系信息 + 老师信息"""

    relation_id: int = Field(description="关系记录ID")
    class_id: int = Field(description="班级ID")
    relation_type: str = Field(description="关系类型：班主任/授课老师")
    relation_created_at: datetime = Field(description="建立关系的时间")
    teacher: TeacherRead = Field(description="老师信息")
