# 班级的 pydantic 校验模型
# 作用：前端传过来的数据，先在这里检查格式

from datetime import date
from pydantic import BaseModel, Field




class ClassCreate(BaseModel):
    """新增班级入参"""
    class_no: str = Field(..., max_length=50, description="班级编号（如 WL2024-A）")
    class_name: str = Field(..., max_length=50, description="班级名称")
    start_date: date | None = Field(None, description="开课时间")
    completion_date: date | None = Field(None, description="结课时间")
    class_status: str | None = Field(None, max_length=20, description="班级状态")

    # 方便前端录入时直接选择老师
    # 接收前端传递的班主任 / 授课老师主键ID，用于后续中间表关联持久化
    head_teacher_id: int | None = Field(None, description="班主任的ID（来自teachers表）")
    teacher_id: int | None = Field(None, description="授课老师的ID（来自teachers表）")


class ClassUpdate(BaseModel):
    """更新班级"""
    class_name: str | None = Field(None, max_length=50)
    start_date: date | None = Field(None)
    completion_date: date | None = Field(None)
    class_status: str | None = Field(None, max_length=20)