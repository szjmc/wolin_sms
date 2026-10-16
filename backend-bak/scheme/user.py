"""认证请求、用户响应和密码校验模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scheme.common import UserRole


def validate_password_bytes(value: str):
    """bcrypt 的限制按 UTF-8 字节计算，而不是按中文字符数量计算。"""

    if len(value.encode("utf-8")) > 72:
        raise ValueError("密码 UTF-8 长度不能超过 72 字节")
    return value


class UserRegister(BaseModel):
    """注册或管理员新建用户的请求体。"""

    model_config = ConfigDict(use_enum_values=True, validate_default=True)

    username: str = Field(min_length=3, max_length=50, description="登录账号")
    password: str = Field(min_length=6, max_length=72, description="登录密码")
    display_name: str = Field(min_length=1, max_length=50, description="显示名称")
    role: UserRole = Field(default=UserRole.VIEWER, description="用户角色")
    class_id: int | None = Field(default=None, gt=0, description="教师类角色所属班级")

    @field_validator("username", "display_name", mode="before")
    @classmethod
    def trim_text(cls, value):
        # 账号和姓名可清理首尾空格，但密码必须保留原始输入。
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        return validate_password_bytes(value)

    @model_validator(mode="after")
    def check_class_for_teacher(self):
        if self.role in ("head_teacher", "teacher") and self.class_id is None:
            raise ValueError("班主任和授课老师必须填写所属班级 class_id")
        return self


class UserUpdate(BaseModel):
    """用户管理 PATCH 请求体；未提交字段表示不修改。"""

    model_config = ConfigDict(use_enum_values=True)

    password: str | None = Field(default=None, min_length=6, max_length=72)
    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    role: UserRole | None = None
    class_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        return validate_password_bytes(value) if value is not None else value

    @model_validator(mode="after")
    def check_nullable_fields(self):
        # 密码、姓名、角色和启停状态显式传 null 都表示请求错误；class_id 允许显式清空。
        for name in ("password", "display_name", "role", "is_active"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} 不能为 null；不修改请不要提交该字段")
        return self


class UserLogin(BaseModel):
    """登录请求体。"""

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        return validate_password_bytes(value)


class ChangePassword(BaseModel):
    """当前用户修改密码的请求体。"""

    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=6, max_length=72)

    @field_validator("current_password", "new_password")
    @classmethod
    def check_password(cls, value):
        return validate_password_bytes(value)


class AuthStatus(BaseModel):
    """公开接口只返回系统是否已经初始化。"""

    initialized: bool


class UserRead(BaseModel):
    """安全用户响应，明确排除 password_hash 和 token。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: str
    class_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginResult(BaseModel):
    """登录成功返回的令牌和用户资料。"""

    token: str = Field(description="Authorization: Bearer <token>")
    user: UserRead
