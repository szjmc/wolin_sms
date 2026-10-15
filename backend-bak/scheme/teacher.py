# -*- coding: utf-8 -*-
"""
老师模块的 Pydantic 校验模型
============================
字段名与数据库保持一致（snake_case）。
"""
from datetime import datetime
from pydantic import BaseModel, Field


class TeacherCreate(BaseModel):
    """新增老师时的请求体"""
    teacher_code: str = Field(..., max_length=32, description="老师编号")
    name: str = Field(..., max_length=64, description="老师姓名")
    phone: str | None = Field(None, max_length=32, description="联系电话")
    status: int = Field(1, description="状态：1启用 0停用")


class TeacherUpdate(BaseModel):
    """
    更新老师时的请求体。
    所有字段可选，前端传哪个就改哪个。
    teacher_code 一般不允许修改。
    """
    name: str | None = Field(None, max_length=64)
    phone: str | None = Field(None, max_length=32)
    status: int | None = Field(None)


class TeacherOut(BaseModel):
    """返回给前端的老师数据结构"""
    id: int
    teacher_code: str
    name: str
    phone: str | None = None
    status: int
    created_at: datetime | None = None
    updated_at: datetime | None = None