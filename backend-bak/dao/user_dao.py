"""users 表数据访问层，只负责查询和持久化，不放角色业务判断。"""
from datetime import datetime

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from model.user import User


def get_user_by_id(db: Session, user_id: int):
    """按 ID 查询未逻辑删除用户。"""

    return db.query(User).filter(User.id == user_id, User.is_deleted == 0).first()


def get_user_by_username(db: Session, username: str):
    """按用户名查询，包含逻辑删除记录，用于登录和唯一性校验。"""

    return db.query(User).filter(User.username == username).first()


def get_user_by_token(db: Session, token: str):
    """只返回未删除且启用中的 token 用户。"""

    return (
        db.query(User)
        .filter(User.token == token, User.is_deleted == 0, User.is_active == 1)
        .first()
    )


def list_users(db: Session, page: int, page_size: int, username: str | None = None, role: str | None = None):
    """分页查询未删除用户；username 按前端的“账号关键词”进行模糊匹配。"""

    query = db.query(User).filter(User.is_deleted == 0)
    username = clean_text(username)
    if username:
        query = query.filter(User.username.like(f"%{username}%"))
    if role:
        query = query.filter(User.role == role)
    query = query.order_by(User.id.asc())
    return paginate(query, page, page_size)


def class_exists(db: Session, class_id: int) -> bool:
    """
    查询班级是否存在，不导入 backend-bak 中会重复注册旧表的 class_info 模型。

    旧班级模型缺少 is_deleted 字段，而正式 SQL 可能包含该字段，
    所以先读取现有表列，再决定是否追加逻辑删除条件。
    """

    inspector = inspect(db.get_bind())
    columns = {column["name"] for column in inspector.get_columns("classes")}
    conditions = ["id = :class_id"]
    if "is_deleted" in columns:
        conditions.append("is_deleted = 0")
    statement = text(
        "SELECT id FROM classes WHERE " + " AND ".join(conditions) + " LIMIT 1"
    )
    return db.execute(statement, {"class_id": class_id}).first() is not None


def create_user(db: Session, data: dict):
    """新增用户；调用方必须提前把明文密码转换为 password_hash。"""

    user = User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, changes: dict):
    """只更新 changes 中出现的字段。"""

    for field_name, value in changes.items():
        setattr(user, field_name, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User):
    """逻辑删除用户并立即撤销其旧令牌。"""

    user.is_deleted = 1
    user.token = None
    user.deleted_at = datetime.now()
    db.commit()
