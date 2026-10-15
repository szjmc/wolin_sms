"""
pytest 公共夹具
===============
测试只连接 MySQL，不再兼容其他数据库。

运行前请准备一个专用测试库（测试开始时会清空并重建表，千万不要用正式库）：

    CREATE DATABASE wolin_student_test DEFAULT CHARACTER SET utf8mb4;

然后：

    export WOLIN_TEST_DB_URL="mysql+pymysql://root:123456@127.0.0.1:3306/wolin_student_test?charset=utf8mb4"
    pytest tests -v
"""
import os
import sys

import pytest

# 第 1 步：必须配置 MySQL 测试库地址，防止误连正式库或其它数据库
TEST_DB_URL = os.getenv("WOLIN_TEST_DB_URL", "")
if not TEST_DB_URL:
    raise RuntimeError(
        "请先设置环境变量 WOLIN_TEST_DB_URL。"
        "测试只支持 MySQL，例如 mysql+pymysql://root:123456@127.0.0.1:3306/wolin_student_test?charset=utf8mb4"
    )
if not TEST_DB_URL.startswith("mysql"):
    raise RuntimeError(
        "生产测试必须直接使用 MySQL。"
        f"当前 WOLIN_TEST_DB_URL 不是 mysql 开头：{TEST_DB_URL}"
    )

# 第 2 步：让后端连上测试库，并把 backend 目录加入导入路径
os.environ["WOLIN_DB_URL"] = TEST_DB_URL
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from database import Base, engine  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def reset_database():
    """整个测试会话开始时，清空并重建全部表，保证环境干净。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    """每个用例拿到一个 FastAPI 测试客户端。"""
    return TestClient(app)
