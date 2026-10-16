"""
管理员账号恢复工具（只能在部署终端执行，不提供公开的免登录重置接口）。

从项目根目录运行：
    python backend/reset_admin.py --list
    python backend/reset_admin.py --username admin
    python backend/reset_admin.py --username admin --create-if-missing --generate

默认用 getpass 隐藏输入新密码；--generate 生成随机临时密码，仅在本次终端输出。
只修改指定管理员账号，不删除数据库，不重建表，不触碰业务数据。
"""
import argparse
import getpass
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv


def restore_admin(db, username, password, create_if_missing=False):
    """基础事务：查账号、校验身份、设置 bcrypt 密码、撤销旧令牌、提交。"""
    from datetime import datetime
    from model.user import User
    from security import hash_password

    # 先校验并加密，再接触数据库，防止无效密码改变现有账号。
    password_hash = hash_password(password)
    user = db.query(User).filter(User.username == username).with_for_update().first()
    if user is None:
        if not create_if_missing:
            raise ValueError("账号不存在；需要创建新管理员时请显式添加 --create-if-missing")
        user = User(username=username, password_hash=password_hash, display_name="系统管理员", role="admin", is_active=1)
        db.add(user)
    else:
        if user.role != "admin":
            raise ValueError("该账号不是管理员，拒绝自动提权；请选择管理员账号或新的专用账号名")
        # 只恢复管理员的密码和可用状态；保留原主键、姓名、创建时间。
        user.password_hash = password_hash
        user.token = None
        user.is_active = 1
        user.is_deleted = 0
        user.deleted_at = None
        user.updated_at = datetime.now()
    db.commit()
    return username


def main():
    parser = argparse.ArgumentParser(description="恢复管理员密码，不清空业务数据")
    parser.add_argument("--username", default="admin", help="要恢复的管理员账号")
    parser.add_argument("--list", action="store_true", help="只列出管理员账号名与状态，不输出密码或令牌")
    parser.add_argument("--create-if-missing", action="store_true", help="账号不存在时允许创建新管理员")
    parser.add_argument("--generate", action="store_true", help="生成随机临时密码，成功后仅输出一次")
    args = parser.parse_args()

    load_dotenv(Path(__file__).parent / ".env")
    url = os.getenv("WOLIN_DB_URL", "")
    if not url.startswith("mysql+pymysql://"):
        parser.error("请先在 backend/.env 配置真实 MySQL 的 WOLIN_DB_URL；本工具不会猜测数据库地址")
    username = args.username.strip()
    if not 3 <= len(username) <= 50:
        parser.error("账号长度必须是 3–50 字符")

    # 延迟导入：--help 不连接数据库。不要导入 main，避免触发自动建表。
    from database import SessionLocal
    from model.user import User
    db = SessionLocal()
    try:
        if args.list:
            rows = db.query(User).filter(User.role == "admin").order_by(User.id).all()
            for row in rows:
                print(f"ID={row.id} 账号={row.username} 启用={row.is_active} 已删除={row.is_deleted}")
            return
        password = os.getenv("WOLIN_ADMIN_PASSWORD")
        if args.generate:
            password = "Wl!" + secrets.token_urlsafe(12)
        elif not password:
            password = getpass.getpass("新密码（输入不可见）：")
            if password != getpass.getpass("再次输入新密码："):
                raise ValueError("两次密码不一致，未修改任何数据")
        restore_admin(db, username, password, args.create_if_missing)
        print(f"管理员 {username} 已恢复。旧令牌已撤销，业务数据未更改。")
        if args.generate:
            print(f"临时密码（仅本次终端输出）：{password}")
        print("请通过根路径登录，然后在个人信息页面修改密码。")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # 不打印连接串或数据库驱动堆栈，避免终端日志暴露密码。
        if isinstance(error, ValueError):
            raise SystemExit(str(error))
        raise SystemExit("恢复失败，未提交修改。请检查 MySQL 服务、连接配置及 users 表是否已初始化。")
