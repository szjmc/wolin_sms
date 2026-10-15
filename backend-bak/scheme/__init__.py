# -*- coding: utf-8 -*-
"""
老师模块的 Pydantic 校验模型
============================
作用：校验前端传来的数据是否合法。
    1. TeacherCreate：新增老师时的请求体
    2. TeacherUpdate：更新老师时的请求体（所有字段可选）
    3. TeacherOut：返回给前端的老师数据结构
"""
from pydantic import BaseModel, Field


class TeacherCreate(BaseModel):
    """新增老师时的请求体"""
    teacher_id: str = Field(..., max_length=20, description="老师编号")
    name: str = Field(..., max_length=50, description="老师姓名")
    gender: str | None = Field(None, max_length=4, description="性别")
    phone: str | None = Field(None, max_length=20, description="联系电话")
    subject: str | None = Field(None, max_length=50, description="教授科目/方向")
    title: str | None = Field(None, max_length=50, description="职称")


class TeacherUpdate(BaseModel):
    """
    更新老师时的请求体。
    所有字段都是可选的，前端传哪个就改哪个。
    注意：teacher_id 不允许修改。
    """
    name: str | None = Field(None, max_length=50)
    gender: str | None = Field(None, max_length=4)
    phone: str | None = Field(None, max_length=20)
    subject: str | None = Field(None, max_length=50)
    title: str | None = Field(None, max_length=50)


class TeacherOut(BaseModel):
    """返回给前端的老师数据结构"""
    teacher_id: str
    name: str
    gender: str | None = None
    phone: str | None = None
    subject: str | None = None
    title: str | None = None