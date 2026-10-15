"""
公共 Pydantic 模型
==================

[补全说明] backend-bak 原缺少公共响应、分页、错误模型及枚举定义，导致老师和就业等
路由无法导入。本文件保持小组现有的 Pydantic v2 技术栈，并对齐 backend 的公共接口契约。
"""
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一成功响应：{"code": 0, "message": "success", "data": ...}"""

    code: int = Field(default=0, description="业务码，0 表示成功")
    message: str = Field(default="success", description="提示信息")
    data: T = Field(description="业务数据")


class PageData(BaseModel, Generic[T]):
    """统一分页数据。"""

    items: list[T] = Field(description="当前页的数据列表")
    total: int = Field(description="符合条件的总条数")
    page: int = Field(description="当前页码，从 1 开始")
    page_size: int = Field(description="每页条数")


class ErrorDetail(BaseModel):
    """参数校验等错误的字段明细。"""

    field: str | None = Field(default=None, description="出错字段")
    reason: str = Field(description="出错原因")


class ErrorResponse(BaseModel):
    """统一错误响应。"""

    code: int = Field(description="业务错误码")
    message: str = Field(description="错误提示")
    details: list[ErrorDetail] = Field(default_factory=list, description="错误明细")


class Gender(str, Enum):
    MALE = "男"
    FEMALE = "女"
    OTHER = "其他"


class SalaryPeriod(str, Enum):
    MONTH = "MONTH"
    YEAR = "YEAR"


class ClassStatus(str, Enum):
    NOT_STARTED = "未开班"
    STUDYING = "在读"
    FINISHED = "已结课"


class TeacherStatus(str, Enum):
    ACTIVE = "在职"
    LEFT = "离职"


# [修改说明] 原代码：公共枚举只有任职状态 TeacherStatus；修改原因：前端把“是否在职”和“是否可授课”分开维护，缺少枚举会接受任意 teaching_status；修改为：新增可授课/暂停授课枚举，供老师表单、筛选和排班校验共用。
class TeachingStatus(str, Enum):
    AVAILABLE = "可授课"
    PAUSED = "暂停授课"


class RelationType(str, Enum):
    HEAD_TEACHER = "班主任"
    LECTURER = "授课老师"


def check_not_null(model: BaseModel, field_names: list[str]):
    """PATCH 时阻止数据库必填字段被显式传为 null。"""
    for field_name in field_names:
        if field_name in model.model_fields_set and getattr(model, field_name) is None:
            raise ValueError(f"字段 {field_name} 不能为空")
