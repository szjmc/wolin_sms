"""认证角色权限规则。"""
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from model.user import User


ROLE_RULES = {
    "admin": ["*"],
    "head_teacher": ["student", "score", "employment", "class", "user"],
    "teacher": ["score"],
    "employment": ["employment"],
    "viewer": [],
}

# admin 和 employment 可以跨班级，其余带班角色只能操作自己的班级。
CROSS_CLASS_ROLES = {"admin", "employment"}


def can_operate_module(user: "User", module: str) -> bool:
    """判断角色是否拥有指定模块权限。"""

    allowed = ROLE_RULES.get(user.role, [])
    return "*" in allowed or module in allowed


def check_permission(user: "User", module: str, class_id: int | None = None):
    """先校验模块权限，再校验需要时的班级范围。"""

    if not can_operate_module(user, module):
        raise HTTPException(status_code=403, detail=f"当前角色（{user.role}）无权操作该功能")
    if class_id is None or user.role in CROSS_CLASS_ROLES:
        return
    if user.class_id != class_id:
        raise HTTPException(status_code=403, detail="只能操作自己负责班级的数据")
