"""users 表 ORM 模型。密码哈希和登录令牌不会直接返回给前端。"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class User(Base):
    """登录用户、角色和逻辑删除状态。"""

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="用户主键ID")
    username = Column(String(50), nullable=False, unique=True, comment="登录账号，全表唯一")
    password_hash = Column(String(255), nullable=False, comment="bcrypt 密码哈希")
    display_name = Column(String(50), nullable=False, comment="显示名称")
    role = Column(String(20), nullable=False, default="viewer", comment="用户角色")
    # 不在 ORM 层导入旧班级模型，避免 backend-bak 中重复的学生/成绩表模型互相冲突。
    class_id = Column(BigInteger, nullable=True, comment="班主任或授课老师所属班级ID")
    token = Column(String(64), nullable=True, comment="登录令牌")
    is_active = Column(TINYINT, nullable=False, default=1, server_default="1", comment="是否启用")
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="是否逻辑删除")
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
