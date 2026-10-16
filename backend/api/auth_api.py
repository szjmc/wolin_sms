"""
登录、注册、个人资料和用户管理接口
==================================
密码只存 bcrypt 哈希；所有用户响应都使用 UserRead，不会返回 password_hash。

账号权限：
- 系统首个账号自动成为 admin 管理员。
- admin 和 head_teacher 都能查看、创建、编辑、停用普通用户。
- head_teacher 不能创建管理员、不能修改/删除管理员账号，不能把普通账号提升为管理员。
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, get_current_user, page_data, require_user_by_header, success
from api.permissions import check_permission
from dao import class_dao, user_dao
from database import get_db
from model.user import User
from scheme.common import ApiResponse, PageData, UserRole
from scheme.user import AuthStatus, ChangePassword, LoginResult, UserLogin, UserRead, UserRegister, UserUpdate
from security import hash_password, make_token, verify_password

router = APIRouter(tags=["登录与用户"], responses=ERROR_RESPONSES)


def to_user_read(user: User) -> UserRead:
    """把用户对象转成安全的响应模型；password_hash 永远不返回。"""
    return UserRead.model_validate(user)


def create_user_from_payload(db: Session, payload: UserRegister, role_value: str | None = None):
    """校验班级并创建用户；密码在这里加密，DAO 只收到哈希。"""
    if user_dao.get_user_by_username(db, payload.username) is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")

    role = role_value or payload.role
    class_id = payload.class_id
    if role in ("head_teacher", "teacher") and class_id is None:
        raise HTTPException(status_code=422, detail="班主任和授课老师必须填写所属班级 class_id")
    if role not in ("head_teacher", "teacher"):
        class_id = None
    if class_id is not None and class_dao.get_class_by_id(db, class_id) is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    user = user_dao.create_user(db, {
        "username": payload.username,
        "password_hash": hash_password(payload.password),
        "display_name": payload.display_name,
        "role": role,
        "class_id": class_id,
    })
    return user


@router.get("/auth/status", response_model=ApiResponse[AuthStatus], summary="查询是否已初始化账号")
def auth_status(db: Session = Depends(get_db)):
    # 只检查账号表，不检查学生表；已删除账号也意味着系统曾经初始化。
    return success(AuthStatus(initialized=db.query(User.id).first() is not None))


@router.post("/auth/register", response_model=ApiResponse[UserRead], status_code=201, summary="注册账号")
def register(
    payload: UserRegister,
    authorization: str | None = Header(default=None, description="系统首次初始化不带令牌；之后需要管理员或班主任令牌"),
    db: Session = Depends(get_db),
):
    """系统第一个账号自动成为管理员；之后访客可自助注册只读账号，管理角色由管理员创建。"""
    initialized = db.query(User.id).first() is not None
    if not initialized:
        # 系统一个账号都没有：第一个注册的账号自动成为管理员
        user = create_user_from_payload(db, payload, role_value="admin")
        return success(to_user_read(user))

    # 系统已有账号：带令牌且是管理员/班主任时，按请求角色创建账号
    current = None
    if authorization:
        try:
            current = require_user_by_header(db, authorization)
        except HTTPException:
            current = None
    if current is not None and current.role in ("admin", "head_teacher"):
        if current.role != "admin" and payload.role == "admin":
            raise HTTPException(status_code=403, detail="只有管理员可以创建管理员账号")
        user = create_user_from_payload(db, payload)
        return success(to_user_read(user))

    # 普通访客自助注册：只允许只读账号，防止匿名创建越权账号
    if payload.role != "viewer":
        raise HTTPException(
            status_code=403,
            detail="班主任、授课老师、就业专员和管理员账号需由管理员创建；访客可先注册只读账号",
        )
    user = create_user_from_payload(db, payload, role_value="viewer")
    return success(to_user_read(user))


@router.post("/auth/login", response_model=ApiResponse[LoginResult], summary="登录")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    # 账号不存在、逻辑删除和密码错误统一提示，避免泄露有效账号列表。
    user = user_dao.get_user_by_username(db, payload.username)
    if user is None or user.is_deleted == 1:
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if user.is_active != 1:
        raise HTTPException(status_code=403, detail="账号已被停用，请联系管理员")

    token = make_token()
    user = user_dao.update_user(db, user, {"token": token})
    return success(LoginResult(token=token, user=to_user_read(user)))


@router.post("/auth/logout", response_model=ApiResponse[None], summary="退出登录")
def logout(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """清空令牌，退出后旧 token 马上失效。"""
    user_dao.update_user(db, current, {"token": None})
    return success(None)


@router.post("/auth/change-password", response_model=ApiResponse[None], summary="当前用户修改自己的密码")
def change_password(payload: ChangePassword, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """本人改密码：先验证旧密码，再加密新密码，清空令牌并要求重新登录。"""
    if not verify_password(payload.current_password, current.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    user_dao.update_user(db, current, {"password_hash": hash_password(payload.new_password), "token": None})
    return success(None)


@router.get("/auth/me", response_model=ApiResponse[UserRead], summary="查看当前登录用户")
def me(current: User = Depends(get_current_user)):
    """返回当前账号的安全资料，不包含密码哈希。"""
    return success(to_user_read(current))


@router.get("/users", response_model=ApiResponse[PageData[UserRead]], summary="用户列表（管理员和班主任）")
def list_users(
    username: str | None = Query(default=None, description="登录账号（精确匹配）"),
    role: UserRole | None = Query(default=None, description="角色"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 管理员和班主任都可以查看所有账号信息。
    check_permission(current, "user")
    users, total = user_dao.list_users(db, page, page_size, username=username, role=role.value if role else None)
    return success(page_data([to_user_read(user) for user in users], total, page, page_size))


@router.post("/users", response_model=ApiResponse[UserRead], status_code=201, summary="新建用户（管理员和班主任）")
def create_managed_user(payload: UserRegister, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_permission(current, "user")
    if current.role != "admin" and payload.role == "admin":
        raise HTTPException(status_code=403, detail="班主任不能创建管理员账号")
    return success(to_user_read(create_user_from_payload(db, payload)), )


@router.get("/users/{user_id}", response_model=ApiResponse[UserRead], summary="用户详情（管理员和班主任）")
def get_managed_user(user_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_permission(current, "user")
    user = user_dao.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在或已删除")
    return success(to_user_read(user))


@router.patch("/users/{user_id}", response_model=ApiResponse[UserRead], summary="编辑用户（管理员和班主任）")
def update_user(user_id: int, payload: UserUpdate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_permission(current, "user")
    user = user_dao.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在或已删除")

    # 班主任可以管理普通账号，但不能改管理员，也不能创建管理员权限。
    if current.role != "admin" and user.role == "admin":
        raise HTTPException(status_code=403, detail="班主任不能修改管理员账号")
    if current.role != "admin" and payload.role == "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以授予管理员角色")

    changes = payload.model_dump(exclude_unset=True)
    new_role = changes.get("role", user.role)
    new_class_id = changes.get("class_id", user.class_id)
    if new_role in ("head_teacher", "teacher") and new_class_id is None:
        raise HTTPException(status_code=422, detail="班主任和授课老师必须绑定所属班级")
    if "class_id" in changes and changes["class_id"] is not None:
        if class_dao.get_class_by_id(db, changes["class_id"]) is None:
            raise HTTPException(status_code=404, detail="班级不存在或已删除")

    if "password" in changes:
        changes["password_hash"] = hash_password(changes.pop("password"))
        changes["token"] = None
    if "is_active" in changes:
        changes["is_active"] = 1 if changes["is_active"] else 0
        if changes["is_active"] == 0:
            changes["token"] = None

    return success(to_user_read(user_dao.update_user(db, user, changes)))


@router.delete("/users/{user_id}", status_code=204, summary="逻辑删除用户（管理员和班主任）")
def delete_user(user_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_permission(current, "user")
    user = user_dao.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在或已删除")
    if user.id == current.id:
        raise HTTPException(status_code=409, detail="不能删除当前登录账号")
    if current.role != "admin" and user.role == "admin":
        raise HTTPException(status_code=403, detail="班主任不能删除管理员账号")
    user_dao.delete_user(db, user)
    return Response(status_code=204)
