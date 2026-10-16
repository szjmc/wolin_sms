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

API = "/api/v1"


@pytest.fixture(scope="session", autouse=True)
def reset_database():
    """
    整个测试会话开始时：清空重建全部表，并先建好一个管理员账号。
    先建管理员是因为"系统第一个账号自动成为管理员"，顺序固定了结果才稳定。
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    bootstrap = TestClient(app)
    bootstrap.post(API + "/auth/register", json={"username": "admin", "password": "admin123", "display_name": "系统管理员"})
    yield


@pytest.fixture()
def anon_client():
    """不带登录态的客户端：用来测试"没登录会被拒绝"这类用例。"""
    return TestClient(app)


@pytest.fixture()
def client(reset_database):
    """管理员客户端：默认所有写操作都带管理员令牌。"""
    return make_client("admin", "admin123")


def make_client(username: str, password: str):
    """登录并返回带令牌的客户端（权限用例里造各种角色用）"""
    test_client = TestClient(app)
    response = test_client.post(API + "/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    test_client.headers.update({"Authorization": f"Bearer {response.json()['data']['token']}"})
    return test_client


def register_user(client, username, password, display_name, role="viewer", class_id=None):
    """用管理员客户端注册一个账号，返回用户数据"""
    body = {"username": username, "password": password, "display_name": display_name, "role": role}
    if class_id is not None:
        body["class_id"] = class_id
    response = client.post(API + "/auth/register", json=body)
    assert response.status_code == 201, response.text
    return response.json()["data"]
