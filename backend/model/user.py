"""
用户表 users 的 ORM 模型
========================
登录注册功能的账号表。字段保持简单直白：

1. username：登录账号，全表唯一（含已删除记录）
2. password_hash：bcrypt 加密后的密码，绝不存明文
3. role：角色，决定这个账号能操作哪些数据
4. class_id：班主任/授课老师所属班级；管理员、就业专员可以为空
5. token：登录成功后生成的令牌，后续请求凭 Authorization 头找到用户
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class User(Base):
    """用户表"""

    __tablename__ = "users"

    # 主键：BIGINT 自增
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="用户主键ID")
    # 登录账号：全局唯一，不允许为空
    username = Column(String(50), nullable=False, unique=True, comment="登录账号，全局唯一")
    # 密码哈希：bcrypt 加密结果，长度固定 60 字符左右，给足 255 位
    password_hash = Column(String(255), nullable=False, comment="bcrypt 加密后的密码，绝不存明文")
    # 显示名称：列表里展示用，比如老师姓名
    display_name = Column(String(50), nullable=False, comment="显示名称")
    # 角色：admin / head_teacher / teacher / employment / viewer
    role = Column(String(20), nullable=False, default="viewer", comment="角色：admin/head_teacher/teacher/employment/viewer")
    # 所属班级：班主任和授课老师用；管理员、就业专员为空
    class_id = Column(BigInteger, nullable=True, comment="所属班级ID（班主任/授课老师用）")
    # 登录令牌：登录成功时生成，退出登录时清空
    token = Column(String(64), nullable=True, comment="登录令牌")
    # 账号是否启用：0=停用（停用后不能登录）
    is_active = Column(TINYINT, nullable=False, default=1, server_default="1", comment="账号是否启用：1=启用，0=停用")

    # ========== 公共字段：逻辑删除 + 时间戳 ==========
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
