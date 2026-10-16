"""
认证与公共响应模型
==================
本文件只放跨接口复用的响应外壳、分页结构、错误明细和角色枚举，
不放学生、班级等业务模型，避免认证模块导入无关的旧模型。
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
    """统一分页数据，字段名称与前端 PageResult 保持一致。"""

    items: list[T] = Field(description="当前页数据")
    total: int = Field(description="符合筛选条件的总数量")
    page: int = Field(description="当前页码，从 1 开始")
    page_size: int = Field(description="每页数量")


class ErrorDetail(BaseModel):
    """参数校验错误明细。"""

    field: str | None = Field(default=None, description="出错字段")
    reason: str = Field(description="错误原因")


class ErrorResponse(BaseModel):
    """统一错误响应：业务码由 HTTP 状态码转换而来。"""

    code: int = Field(description="业务错误码")
    message: str = Field(description="错误提示")
    details: list[ErrorDetail] = Field(default_factory=list, description="错误明细")


class SalaryPeriod(str, Enum):
    """保留旧接口已经引用的薪资周期枚举，避免公共模块接入后破坏旧导入。"""

    MONTH = "MONTH"
    YEAR = "YEAR"


class TeacherStatus(str, Enum):
    """保留旧教师接口已经引用的教师状态枚举。"""

    ACTIVE = "在职"
    LEFT = "离职"


class UserRole(str, Enum):
    """认证模块支持的五种角色。"""

    ADMIN = "admin"
    HEAD_TEACHER = "head_teacher"
    TEACHER = "teacher"
    EMPLOYMENT = "employment"
    VIEWER = "viewer"


def check_not_null(model: BaseModel, field_names: list[str]):
    """检查 PATCH 请求中不允许被显式清空的字段。"""

    for field_name in field_names:
        if field_name in model.model_fields_set and getattr(model, field_name) is None:
            raise ValueError(f"字段 {field_name} 不能为空")
