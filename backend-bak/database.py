"""
数据库连接初始化
================
本文件只做 4 件事：
1. 读取数据库连接地址
2. 创建数据库引擎 engine
3. 创建会话工厂 SessionLocal
4. 提供 Base（所有 ORM 模型的父类）和 get_db（给 FastAPI 接口注入数据库会话）
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# [修改说明] 原注释固定写成 backend/.env；修改原因：backend-bak 已可独立运行，固定目录名会让配置步骤产生歧义；修改为：始终读取当前后端目录（BASE_DIR）中的 .env。
# 第 1 步：加载当前后端目录的 .env（文件不存在也没关系）
# 明确指定当前文件所在目录，避免误读项目根目录或另一套后端的配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# 第 2 步：读取数据库连接地址
# 格式：mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4
# 没有配置环境变量 WOLIN_DB_URL 时，使用下面的默认值（本地开发用）
DATABASE_URL = os.getenv(
    "WOLIN_DB_URL",
    "mysql+pymysql://root:123456@127.0.0.1:3306/wolin_student?charset=utf8mb4",
)

# 第 3 步：创建数据库引擎
# pool_pre_ping=True：从连接池取连接前先检测连接是否可用，避免 MySQL 断开空闲连接后报错
# pool_recycle=3600：连接用满 1 小时就重建，防止被 MySQL 的 wait_timeout 断开
# echo=False：不打印 SQL；调试时可以改成 True，在控制台查看执行的每一条 SQL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

# 第 4 步：创建会话工厂，每个请求都用它创建一个新的数据库会话
# autocommit=False：必须手动调用 db.commit() 才会提交事务
# autoflush=False：不自动把修改刷到数据库，代码行为更容易理解
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# 第 5 步：所有 ORM 模型都继承这个 Base
Base = declarative_base()


def get_db():
    """
    获取数据库会话（给 FastAPI 依赖注入使用）。

    用法：def 接口函数(db: Session = Depends(get_db))
    请求开始时创建会话；请求结束后（无论成功还是报错）都会自动关闭会话。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
