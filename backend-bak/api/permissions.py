"""
权限规则（保持非常简单）
========================
一张字典说清楚每个角色能干什么、能不能跨班级操作：

| 角色 | 能操作的模块 | 能操作的范围 |
|---|---|---|
| admin 管理员 | 全部（含班级/老师建档、账号管理） | 全部班级 |
| head_teacher 班主任 | 学生 / 成绩 / 就业 | 只限自己带的班级 |
| teacher 授课老师 | 成绩 | 只限自己带的班级 |
| employment 就业专员 | 就业 | 全部班级 |
| viewer 只读 | 无 | 只能查看 |

前端和后端用同一套说法：没有权限就返回 403，不做任何写操作。
"""
from fastapi import HTTPException

from model.user import User

# 每个角色可以操作哪些模块（"*" 表示全部）
ROLE_RULES = {
    # setup = 班级建档、老师建档、账号管理这类"组织配置"操作，只给管理员
    "admin": ["*"],
    # 管理层（班主任）可以查看全部账号并管理非管理员账号；不能授予/修改 admin 角色。
    "head_teacher": ["student", "score", "employment", "class", "user"],
    "teacher": ["score"],
    "employment": ["employment"],
    "viewer": [],
}

# 哪些角色可以跨班级操作（其余角色只能操作自己 class_id 对应的班级）
CROSS_CLASS_ROLES = ["admin", "employment"]


def can_operate_module(user: User, module: str) -> bool:
    """这个角色能不能操作这个模块（比如 head_teacher 能操作 student，viewer 不能）"""
    allowed = ROLE_RULES.get(user.role, [])
    return "*" in allowed or module in allowed


def check_permission(user: User, module: str, class_id: int | None = None):
    """
    校验权限，不通过直接抛 403。

    两个判断，顺序很简单：
    1. 这个角色允许操作这个模块吗？
    2. 如果只能操作自己的班级，class_id 是不是自己的班？
    """
    if not can_operate_module(user, module):
        raise HTTPException(status_code=403, detail=f"当前角色（{user.role}）无权操作该功能")

    # 没有指定班级的接口（比如新增用户）只做第 1 步校验
    if class_id is None:
        return

    if user.role in CROSS_CLASS_ROLES:
        return

    # 班主任 / 授课老师只能操作自己带的那个班
    if user.class_id != class_id:
        raise HTTPException(status_code=403, detail="只能操作自己负责班级的数据")
