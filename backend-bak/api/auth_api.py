"""登录、注册、个人资料和用户管理接口。"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, get_current_user, page_data, require_user_by_header, success
from api.permissions import check_permission
from dao import user_dao
from database import get_db
from model.user import User
from scheme.common import ApiResponse, PageData, UserRole
from scheme.user import AuthStatus, ChangePassword, LoginResult, UserLogin, UserRead, UserRegister, UserUpdate
from security import hash_password, make_token, verify_password


router = APIRouter(tags=["登录与用户"], responses=ERROR_RESPONSES)


def _role_value(role) -> str:
    """兼容 Pydantic 已转换的字符串和仍为 Enum 的角色值。"""

    return role.value if isinstance(role, UserRole) else str(role)


def to_user_read(user: User) -> UserRead:
    """转换为安全用户响应，明确不返回 password_hash 和 token。"""

    return UserRead.model_validate(user)


def create_user_from_payload(db: Session, payload: UserRegister, role_value: str | None = None):
    """校验用户和班级后创建账号；DAO 只接收加密后的密码。"""

    if user_dao.get_user_by_username(db, payload.username) is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")

    role = role_value or _role_value(payload.role)
    class_id = payload.class_id
    if role in ("head_teacher", "teacher") and class_id is None:
        raise HTTPException(status_code=422, detail="班主任和授课老师必须填写所属班级 class_id")
    if role not in ("head_teacher", "teacher"):
        # 保持 users 表约定：管理员、就业专员和只读用户不绑定班级。
        class_id = None
    if class_id is not None and not user_dao.class_exists(db, class_id):
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    user = user_dao.create_user(
        db,
        {
            "username": payload.username,
            "password_hash": hash_password(payload.password),
            "display_name": payload.display_name,
            "role": role,
            "class_id": class_id,
        },
    )
    return user


@router.get("/auth/status", response_model=ApiResponse[AuthStatus], summary="查询是否已初始化账号")
def auth_status(db: Session = Depends(get_db)):
    """只检查 users 表是否有记录，不公开账号或凭据。"""

    return success(AuthStatus(initialized=db.query(User.id).first() is not None))


@router.post("/auth/register", response_model=ApiResponse[UserRead], status_code=201, summary="注册账号")
def register(
    payload: UserRegister,
    authorization: str | None = Header(default=None, description="首次初始化不带令牌；管理建号需要令牌"),
    db: Session = Depends(get_db),
):
    """
    空库首个账号自动成为管理员；已有账号后匿名注册只允许 viewer，
    admin/head_teacher 可以按权限创建其他角色。
    """

    initialized = db.query(User.id).first() is not None
    if not initialized:
        user = create_user_from_payload(db, payload, role_value="admin")
        return success(to_user_read(user))

    current = None
    if authorization:
        try:
            current = require_user_by_header(db, authorization)
        except HTTPException:
            # 无效令牌不能获得管理权限；若请求角色是 viewer，仍按匿名注册处理。
            current = None

    if current is not None and current.role in ("admin", "head_teacher"):
        if current.role != "admin" and _role_value(payload.role) == "admin":
            raise HTTPException(status_code=403, detail="只有管理员可以创建管理员账号")
        return success(to_user_read(create_user_from_payload(db, payload)))

    if _role_value(payload.role) != "viewer":
        raise HTTPException(
            status_code=403,
            detail="班主任、授课老师、就业专员和管理员账号需由管理员创建；访客可先注册只读账号",
        )
    return success(to_user_read(create_user_from_payload(db, payload, role_value="viewer")))


@router.post("/auth/login", response_model=ApiResponse[LoginResult], summary="登录")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """账号不存在、已删除或密码错误统一返回相同提示，避免泄露账号信息。"""

    user = user_dao.get_user_by_username(db, payload.username)
    if user is None or user.is_deleted == 1 or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if user.is_active != 1:
        raise HTTPException(status_code=403, detail="账号已被停用，请联系管理员")

    token = make_token()
    user = user_dao.update_user(db, user, {"token": token})
    return success(LoginResult(token=token, user=to_user_read(user)))


@router.post("/auth/logout", response_model=ApiResponse[None], summary="退出登录")
def logout(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """清空当前令牌，使退出后的旧 token 立即失效。"""

    user_dao.update_user(db, current, {"token": None})
    return success(None)


@router.post("/auth/change-password", response_model=ApiResponse[None], summary="修改当前用户密码")
def change_password(
    payload: ChangePassword,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """验证旧密码后保存新哈希，并撤销当前令牌要求重新登录。"""

    if not verify_password(payload.current_password, current.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    user_dao.update_user(
        db,
        current,
        {"password_hash": hash_password(payload.new_password), "token": None},
    )
    return success(None)


@router.get("/auth/me", response_model=ApiResponse[UserRead], summary="查看当前登录用户")
def me(current: User = Depends(get_current_user)):
    """返回当前用户的安全资料。"""

    return success(to_user_read(current))


@router.get("/users", response_model=ApiResponse[PageData[UserRead]], summary="用户列表")
def list_users(
    username: str | None = Query(default=None, description="登录账号关键词"),
    role: UserRole | None = Query(default=None, description="角色"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """管理员和班主任可以查看未删除账号列表。"""

    check_permission(current, "user")
    role_value = _role_value(role) if role is not None else None
    users, total = user_dao.list_users(db, page, page_size, username=username, role=role_value)
    return success(page_data([to_user_read(user) for user in users], total, page, page_size))


@router.post("/users", response_model=ApiResponse[UserRead], status_code=201, summary="新建用户")
def create_managed_user(
    payload: UserRegister,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """管理员和班主任建号；班主任不能授予管理员角色。"""

    check_permission(current, "user")
    if current.role != "admin" and _role_value(payload.role) == "admin":
        raise HTTPException(status_code=403, detail="班主任不能创建管理员账号")
    return success(to_user_read(create_user_from_payload(db, payload)))


@router.get("/users/{user_id}", response_model=ApiResponse[UserRead], summary="用户详情")
def get_managed_user(
    user_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回指定的未删除用户。"""

    check_permission(current, "user")
    user = user_dao.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在或已删除")
    return success(to_user_read(user))


@router.patch("/users/{user_id}", response_model=ApiResponse[UserRead], summary="编辑用户")
def update_managed_user(
    user_id: int,
    payload: UserUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """编辑用户资料、角色、班级、密码和启用状态。"""

    check_permission(current, "user")
    user = user_dao.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在或已删除")
    if current.role != "admin" and user.role == "admin":
        raise HTTPException(status_code=403, detail="班主任不能修改管理员账号")

    changes = payload.model_dump(exclude_unset=True)
    new_role = _role_value(changes.get("role", user.role))
    if current.role != "admin" and new_role == "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以授予管理员角色")

    new_class_id = changes.get("class_id", user.class_id)
    if new_role in ("head_teacher", "teacher") and new_class_id is None:
        raise HTTPException(status_code=422, detail="班主任和授课老师必须绑定所属班级")
    if new_role not in ("head_teacher", "teacher"):
        # 修复角色变更后残留 class_id 的数据风险，保持 users 表字段规则一致。
        changes["class_id"] = None
    elif "class_id" in changes or "role" in changes:
        if not user_dao.class_exists(db, new_class_id):
            raise HTTPException(status_code=404, detail="班级不存在或已删除")

    if "password" in changes:
        changes["password_hash"] = hash_password(changes.pop("password"))
        changes["token"] = None
    if "is_active" in changes:
        changes["is_active"] = 1 if changes["is_active"] else 0
        if changes["is_active"] == 0:
            changes["token"] = None

    return success(to_user_read(user_dao.update_user(db, user, changes)))


@router.delete("/users/{user_id}", status_code=204, summary="逻辑删除用户")
def delete_managed_user(
    user_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """逻辑删除账号；删除本人或班主任删除管理员均被拒绝。"""

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
