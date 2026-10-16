"""
公共 Pydantic 模型
==================
1. ApiResponse：统一成功响应外壳 {"code": 0, "message": "success", "data": ...}
2. PageData：统一分页数据 {"items": [], "total": 0, "page": 1, "page_size": 20}
3. ErrorResponse：统一错误响应 {"code": 40401, "message": "...", "details": []}
4. 各种枚举：性别、薪资周期、班级状态、老师状态、班级老师关系类型
5. check_not_null：PATCH 更新时，检查必填字段不能被传成 null
"""
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

# T 是"类型占位符"：ApiResponse[StudentRead] 表示 data 字段的类型是 StudentRead
T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一成功响应外壳：所有接口都返回这个格式"""

    code: int = Field(default=0, description="业务码，0 表示成功")
    message: str = Field(default="success", description="提示信息")
    data: T = Field(description="业务数据")


class PageData(BaseModel, Generic[T]):
    """统一分页数据（放在 ApiResponse 的 data 字段里）"""

    items: list[T] = Field(description="当前页的数据列表")
    total: int = Field(description="符合查询条件的总条数（不是当前页的条数）")
    page: int = Field(description="当前页码，从 1 开始")
    page_size: int = Field(description="每页条数")


class ErrorDetail(BaseModel):
    """错误明细：哪个字段出错、出错原因"""

    field: str | None = Field(default=None, description="出错的字段，如 body.birth_date")
    reason: str = Field(description="出错原因")


class ErrorResponse(BaseModel):
    """统一错误响应格式"""

    code: int = Field(description="业务错误码：40001/40401/40901/42201/50001")
    message: str = Field(description="错误提示信息")
    details: list[ErrorDetail] = Field(default=[], description="错误明细，参数校验失败时列出每个字段的问题")


class Gender(str, Enum):
    """性别"""

    MALE = "男"
    FEMALE = "女"
    OTHER = "其他"


class SalaryPeriod(str, Enum):
    """薪资周期：MONTH=月薪，YEAR=年薪"""

    MONTH = "MONTH"
    YEAR = "YEAR"


class ClassStatus(str, Enum):
    """班级状态"""

    NOT_STARTED = "未开班"
    STUDYING = "在读"
    FINISHED = "已结课"


class TeacherStatus(str, Enum):
    """老师状态"""

    ACTIVE = "在职"
    LEFT = "离职"


class TeachingStatus(str, Enum):
    """老师授课状态"""

    AVAILABLE = "可授课"
    PAUSED = "暂停授课"


class RelationType(str, Enum):
    """班级与老师的关系类型"""

    HEAD_TEACHER = "班主任"
    LECTURER = "授课老师"


class UserRole(str, Enum):
    """账号角色（见 api/permissions.py 的权限表）"""

    ADMIN = "admin"
    HEAD_TEACHER = "head_teacher"
    TEACHER = "teacher"
    EMPLOYMENT = "employment"
    VIEWER = "viewer"


class OfferStatus(str, Enum):
    """就业记录的 Offer 状态"""

    PENDING = "待处理"
    ACCEPTED = "已接受"
    REJECTED = "已拒绝"


def check_not_null(model: BaseModel, field_names: list[str]):
    """
    PATCH 更新时使用：检查"数据库必填字段"不能被客户端显式传成 null。

    model.model_fields_set 里保存的是客户端本次真正提交了的字段名：
    - 没提交的字段：不检查（表示不修改这个字段）
    - 提交了但值是 None：报错（不允许把必填字段清空）
    """
    for field_name in field_names:
        if field_name in model.model_fields_set and getattr(model, field_name) is None:
            raise ValueError(f"字段 {field_name} 不能为空")
