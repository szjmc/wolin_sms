"""用户请求/响应模型：账号可去空格，密码原样保留；bcrypt 密码最多 72 字节。"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from scheme.common import UserRole


def validate_password_bytes(value: str):
    """bcrypt 上限按字节计算，不是按中文字数计算。"""
    if len(value.encode("utf-8")) > 72:
        raise ValueError("密码 UTF-8 长度不能超过 72 字节")
    return value


class UserRegister(BaseModel):
    """新增账号；密码不能被 str_strip_whitespace 自动去空格。"""
    model_config = ConfigDict(use_enum_values=True, validate_default=True)
    username: str = Field(min_length=3, max_length=50, description="登录账号")
    password: str = Field(min_length=6, max_length=72, description="6 个字符以上，UTF-8 最多 72 字节")
    display_name: str = Field(min_length=1, max_length=50, description="显示名称")
    role: UserRole = Field(default="viewer", description="账号角色")
    class_id: int | None = Field(default=None, gt=0, description="教师类角色必须绑定班级")

    @field_validator("username", "display_name", mode="before")
    @classmethod
    def trim_text(cls, value):
        # 只清洗账号与姓名，不改动密码。
        if isinstance(value, str):
            return value.strip()
        return value

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
    """部分更新：不传表示不改；必填项显式 null 会被拒绝。"""
    model_config = ConfigDict(use_enum_values=True)
    password: str | None = Field(default=None, min_length=6, max_length=72, description="重置密码；留空时不要提交字段")
    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    role: UserRole | None = None
    class_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_name(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        if value is not None:
            return validate_password_bytes(value)
        return value

    @model_validator(mode="after")
    def check_fields(self):
        for name in ["password", "display_name", "role", "is_active"]:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} 不能为 null；不修改请不要提交该字段")
        return self


class UserLogin(BaseModel):
    """登录账号可去首尾空格；密码保留原始输入。"""
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        return validate_password_bytes(value)


class ChangePassword(BaseModel):
    """修改本人密码要先验证旧密码；修改后需要重新登录。"""
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=6, max_length=72)

    @field_validator("current_password", "new_password")
    @classmethod
    def check_password(cls, value):
        return validate_password_bytes(value)


class AuthStatus(BaseModel):
    """公开接口只返回初始化标记，不返回任何账号或凭据。"""
    initialized: bool


class UserRead(BaseModel):
    """不包含密码哈希与令牌的账号资料。"""
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
    token: str = Field(description="登录令牌，通过 Authorization: Bearer <token> 传递")
    user: UserRead
