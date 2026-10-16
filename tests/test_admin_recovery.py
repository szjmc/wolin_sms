"""管理员恢复回归：使用现有 MySQL 专用测试库，不测试其他数据库。"""
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from database import SessionLocal
from model.user import User
from reset_admin import restore_admin
from security import hash_password, verify_password
from scheme.user import UserLogin, UserRegister
from tests.helpers import API, ok_data, assert_error


def test_admin_reset_preserves_business_records(client):
    """恢复不依赖账号表为空，不修改学生、班级、成绩等业务行。"""
    from model import ClassInfo, EmploymentRecord, Score, Student
    username = "restore_" + secrets.token_hex(4)
    old_password = secrets.token_urlsafe(16)
    new_password = secrets.token_urlsafe(16)
    with SessionLocal() as db:
        rows_before = [db.query(model).count() for model in [Student, ClassInfo, Score, EmploymentRecord]]
        restore_admin(db, username, old_password, create_if_missing=True)
    login = ok_data(client.post(API + "/auth/login", json={"username": username, "password": old_password}))
    old_token = login["token"]
    with SessionLocal() as db:
        original = db.query(User).filter(User.username == username).one()
        original_id = original.id
        original_created = original.created_at
        restore_admin(db, username, new_password)
        row = db.query(User).filter(User.username == username).one()
        assert row.id == original_id
        assert row.created_at == original_created
        assert row.password_hash.startswith("$2b$")
        assert row.token is None
        assert row.is_active == 1 and row.is_deleted == 0
        assert rows_before == [db.query(model).count() for model in [Student, ClassInfo, Score, EmploymentRecord]]
    assert_error(client.get(API + "/auth/me", headers={"Authorization": "Bearer " + old_token}), 401)
    assert_error(client.post(API + "/auth/login", json={"username": username, "password": old_password}), 400)
    assert ok_data(client.post(API + "/auth/login", json={"username": username, "password": new_password}))["user"]["role"] == "admin"


def test_reset_reactivates_disabled_admin(client):
    username = "disabled_" + secrets.token_hex(4)
    with SessionLocal() as db:
        row = User(username=username, display_name="恢复测试", role="admin", password_hash=hash_password("old-password"), is_active=0, is_deleted=1)
        db.add(row)
        db.commit()
        restore_admin(db, username, "new-password")
        db.refresh(row)
        assert row.is_active == 1 and row.is_deleted == 0
        assert row.deleted_at is None
        assert verify_password("new-password", row.password_hash)


def test_reset_will_not_promote_regular_user(client):
    username = "normal_" + secrets.token_hex(4)
    with SessionLocal() as db:
        row = User(username=username, display_name="普通账号", role="viewer", password_hash=hash_password("normal-password"))
        db.add(row)
        db.commit()
        with pytest.raises(ValueError, match="不是管理员"):
            restore_admin(db, username, "replacement-password")
        db.rollback()
        db.refresh(row)
        assert row.role == "viewer"
        assert verify_password("normal-password", row.password_hash)


def test_missing_admin_requires_explicit_create(client):
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="账号不存在"):
            restore_admin(db, "missing_" + secrets.token_hex(4), "replacement-password")
        db.rollback()


def test_auth_status_only_exposes_initialized(client, anon_client):
    assert ok_data(anon_client.get(API + "/auth/status")) == {"initialized": True}
    # 访客不能匿名创建管理员；只读账号可以自助注册。
    assert_error(anon_client.post(API + "/auth/register", json={"username": "anonymous_" + secrets.token_hex(4), "display_name": "不能越权", "password": "example-password", "role": "admin"}), 403)
    readonly = ok_data(anon_client.post(API + "/auth/register", json={"username": "readonly_" + secrets.token_hex(4), "display_name": "只读访客", "password": "example-password", "role": "viewer"}), 201)
    assert readonly["role"] == "viewer"


def test_corrupt_password_hash_returns_login_error(client, anon_client):
    username = "corrupt_" + secrets.token_hex(4)
    with SessionLocal() as db:
        db.add(User(username=username, display_name="坏哈希", role="admin", password_hash="invalid-hash"))
        db.commit()
    assert_error(anon_client.post(API + "/auth/login", json={"username": username, "password": "example-password"}), 400)


def test_password_bytes_and_whitespace():
    payload = UserRegister(username=" spaceuser ", display_name=" 用户 ", password="  space-password  ")
    assert payload.password == "  space-password  "
    assert payload.username == "spaceuser"
    assert UserLogin(username=" spaceuser ", password=payload.password).password == payload.password
    with pytest.raises(ValueError):
        hash_password("中文" * 13)
    assert not verify_password("中文" * 13, "invalid")


def test_cli_help_does_not_connect_to_database():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "backend/reset_admin.py"), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--create-if-missing" in result.stdout
