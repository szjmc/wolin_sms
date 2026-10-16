"""
用户数据访问层：只负责 users 表的增删改查，不写业务判断
"""
from datetime import datetime

from sqlalchemy.orm import Session

from dao.common import paginate
from model.user import User


def get_user_by_id(db: Session, user_id: int):
    """根据ID查询一个未删除的用户，查不到返回 None"""
    return db.query(User).filter(User.id == user_id, User.is_deleted == 0).first()


def get_user_by_username(db: Session, username: str):
    """
    根据登录账号查询用户（注意：包含已逻辑删除的用户）。
    用于注册时检查账号是否重复——数据库唯一索引对已删除的记录同样生效。
    """
    return db.query(User).filter(User.username == username).first()


def get_user_by_token(db: Session, token: str):
    """根据登录令牌查询用户（只有启用中的账号才认这个令牌）"""
    return (
        db.query(User)
        .filter(User.token == token, User.is_deleted == 0, User.is_active == 1)
        .first()
    )


def list_users(db: Session, page: int, page_size: int, username: str | None = None, role: str | None = None):
    """分页查询未删除的用户，返回 (当前页列表, 总条数)"""
    query = db.query(User).filter(User.is_deleted == 0)
    if username:
        query = query.filter(User.username == username)
    if role:
        query = query.filter(User.role == role)
    query = query.order_by(User.id.asc())
    return paginate(query, page, page_size)


def create_user(db: Session, data: dict):
    """新增用户（data 里必须是加密后的 password_hash，不能是明文）"""
    user = User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, changes: dict):
    """更新用户：只修改 changes 里出现的字段"""
    for field_name, value in changes.items():
        setattr(user, field_name, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User):
    """逻辑删除用户（同时清空令牌，删掉的账号不能再登录）"""
    user.is_deleted = 1
    user.token = None
    user.deleted_at = datetime.now()
    db.commit()
