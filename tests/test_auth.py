"""
登录注册与权限管理：至少 20 条用例。

覆盖三块：
1. 注册：账号唯一、密码长度、角色校验、首个账号自动管理员
2. 登录：bcrypt 密码校验、停用账号、令牌、退出登录
3. 权限：管理员全权；班主任只管自己班；授课老师只管自己班成绩；
   就业专员管就业；只读用户不能写。
"""
import secrets
from tests.conftest import make_client, register_user
from tests.helpers import API, assert_error, create_class, create_student, ok_data


# ---------------- 注册 ----------------
def test_bootstrap_first_user_is_admin(client):
    """系统第一个账号自动成为管理员（测试夹具建的 admin 就是这么来的）。"""
    data = ok_data(client.get(API + "/auth/me"))
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_anonymous_register_readonly_allowed(anon_client):
    """系统已有账号时，访客仍可自助注册只读账号，并自动登录进入系统。"""
    username = "guest_" + secrets.token_hex(4)
    body = {"username": username, "password": "guest123456", "display_name": "自助访客", "role": "viewer"}
    data = ok_data(anon_client.post(API + "/auth/register", json=body), 201)
    assert data["role"] == "viewer"
    assert data["is_active"] is True
    assert ok_data(anon_client.post(API + "/auth/login", json={"username": username, "password": "guest123456"}))["user"]["role"] == "viewer"


def test_anonymous_register_admin_role_rejected(anon_client):
    """访客不能自助注册管理员、就业专员等越权角色（403，需由管理员创建）。"""
    for role in ["admin", "employment"]:
        body = {"username": "hack_" + secrets.token_hex(4), "password": "hack123456", "display_name": "越权尝试", "role": role}
        error = assert_error(anon_client.post(API + "/auth/register", json=body), 403)
        assert "需由管理员创建" in error["message"]


def test_anonymous_register_teacher_role_needs_class(anon_client):
    """教师类角色缺少所属班级时，先被参数校验拦下（422），不会进入越权判断。"""
    for role in ["head_teacher", "teacher"]:
        body = {"username": "hack_" + secrets.token_hex(4), "password": "hack123456", "display_name": "越权尝试", "role": role}
        error = assert_error(anon_client.post(API + "/auth/register", json=body), 422)
        # 422 的 message 是统一提示，具体字段原因在 details 列表里
        assert any("所属班级" in item["reason"] for item in error["details"])


def test_anonymous_register_class_id_ignored(anon_client):
    """访客注册只读账号时，即使传了 class_id 也被服务端忽略，不产生越权绑定。"""
    username = "guest2_" + secrets.token_hex(4)
    body = {"username": username, "password": "guest123456", "display_name": "访客二", "role": "viewer", "class_id": 1}
    data = ok_data(anon_client.post(API + "/auth/register", json=body), 201)
    assert data["class_id"] is None


def test_register_duplicate_username(client):
    register_user(client, "dup01", "dup123456", "重复账号")
    body = {"username": "dup01", "password": "dup123456", "display_name": "另一个"}
    assert_error(client.post(API + "/auth/register", json=body), 409)


def test_register_short_password(client):
    body = {"username": "shortpwd", "password": "123", "display_name": "x"}
    assert_error(client.post(API + "/auth/register", json=body), 422)


def test_register_short_username(client):
    body = {"username": "a", "password": "123456", "display_name": "x"}
    assert_error(client.post(API + "/auth/register", json=body), 422)


def test_head_teacher_needs_class(client):
    body = {"username": "noclass", "password": "123456", "display_name": "x", "role": "head_teacher"}
    assert_error(client.post(API + "/auth/register", json=body), 422)


def test_register_invalid_role(client):
    body = {"username": "badrole", "password": "123456", "display_name": "x", "role": "superman"}
    assert_error(client.post(API + "/auth/register", json=body), 422)


# ---------------- 登录 ----------------
def test_login_success_returns_token(client):
    register_user(client, "login01", "login123", "登录者")
    body = ok_data(client.post(API + "/auth/login", json={"username": "login01", "password": "login123"}))
    assert body["token"]
    assert body["user"]["username"] == "login01"


def test_login_wrong_password(client):
    register_user(client, "login02", "login123", "登录者")
    assert_error(client.post(API + "/auth/login", json={"username": "login02", "password": "wrong!!"}), 400)


def test_login_unknown_user(client):
    """账号不存在与密码错误返回同样提示，避免泄露有效账号列表。"""
    error = assert_error(client.post(API + "/auth/login", json={"username": "nobody", "password": "123456"}), 400)
    assert error["message"] == "用户名或密码错误"


def test_login_inactive_user(client):
    user = register_user(client, "login03", "login123", "登录者")
    ok_data(client.patch(f"{API}/users/{user['id']}", json={"is_active": False}))
    assert_error(client.post(API + "/auth/login", json={"username": "login03", "password": "login123"}), 403)


def test_me_without_token(anon_client):
    assert_error(anon_client.get(API + "/auth/me"), 401)


def test_me_with_bad_token(anon_client):
    assert_error(anon_client.get(API + "/auth/me", headers={"Authorization": "Bearer bad-token"}), 401)


def test_me_with_token(client):
    data = ok_data(client.get(API + "/auth/me"))
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_logout_invalidates_token(client):
    register_user(client, "logout01", "logout123", "退出者")
    user_client = make_client("logout01", "logout123")
    ok_data(user_client.post(API + "/auth/logout"))
    assert_error(user_client.get(API + "/auth/me"), 401)


# ---------------- 用户管理 ----------------
def test_admin_can_create_roles(client):
    class_id = create_class(client, "AU-C-1")["id"]
    for index, role in enumerate(["head_teacher", "teacher", "employment", "viewer"]):
        data = register_user(client, f"user{index}", "user123456", "用户" + str(index), role=role, class_id=class_id if role in ("head_teacher", "teacher") else None)
        assert data["role"] == role


def test_non_admin_cannot_create_user(client):
    class_id = create_class(client, "AU-C-2")["id"]
    register_user(client, "head01", "head123456", "班主任甲", role="head_teacher", class_id=class_id)
    head_client = make_client("head01", "head123456")
    body = {"username": "hack01", "password": "hack123456", "display_name": "x", "role": "admin"}
    assert_error(head_client.post(API + "/auth/register", json=body), 403)


def test_admin_update_password(client):
    user = register_user(client, "changepwd", "oldpass123", "改密者")
    ok_data(client.patch(f"{API}/users/{user['id']}", json={"password": "newpass123"}))
    assert_error(client.post(API + "/auth/login", json={"username": "changepwd", "password": "oldpass123"}), 400)
    ok_data(client.post(API + "/auth/login", json={"username": "changepwd", "password": "newpass123"}))


def test_user_list(client):
    register_user(client, "list01", "list123456", "列表用户")
    page = ok_data(client.get(API + "/users"))
    assert page["total"] >= 2
    for item in page["items"]:
        assert "password_hash" not in item


def test_write_without_token_rejected(anon_client):
    body = {"class_no": "NO-TOKEN", "class_name": "x", "start_date": "2026-03-01"}
    assert_error(anon_client.post(API + "/classes", json=body), 401)


# ---------------- 权限：各司其职 ----------------
def test_head_teacher_only_own_class(client):
    class_a = create_class(client, "AU-C-3A")["id"]
    class_b = create_class(client, "AU-C-3B")["id"]
    register_user(client, "head02", "head123456", "班主任乙", role="head_teacher", class_id=class_a)
    head_client = make_client("head02", "head123456")

    # 自己班的学生可以建
    ok_data(head_client.post(API + "/students", json={"student_no": "AU-S-1", "class_id": class_a, "name": "自己班", "birth_date": "2000-01-01", "gender": "男"}), 201)
    # 别的班不行
    body = {"student_no": "AU-S-2", "class_id": class_b, "name": "别班", "birth_date": "2000-01-01", "gender": "男"}
    assert_error(head_client.post(API + "/students", json=body), 403)


def test_head_teacher_cannot_delete_other_class_student(client):
    class_b = create_class(client, "AU-C-4")["id"]
    student = create_student(client, "AU-S-3", class_b)
    class_a = create_class(client, "AU-C-4A")["id"]
    register_user(client, "head03", "head123456", "班主任丙", role="head_teacher", class_id=class_a)
    head_client = make_client("head03", "head123456")
    assert_error(head_client.delete(f"{API}/students/{student['id']}"), 403)


def test_teacher_can_score_own_class(client):
    class_id = create_class(client, "AU-C-5")["id"]
    student = create_student(client, "AU-S-4", class_id)
    register_user(client, "teach01", "teach123456", "授课老师甲", role="teacher", class_id=class_id)
    teach_client = make_client("teach01", "teach123456")
    data = ok_data(teach_client.post(API + "/scores", json={"student_id": student["id"], "exam_no": 1, "score": 88}), 201)
    assert data["score"] == "88.00"


def test_teacher_cannot_score_other_class(client):
    class_a = create_class(client, "AU-C-6A")["id"]
    class_b = create_class(client, "AU-C-6B")["id"]
    student = create_student(client, "AU-S-5", class_b)
    register_user(client, "teach02", "teach123456", "授课老师乙", role="teacher", class_id=class_a)
    teach_client = make_client("teach02", "teach123456")
    body = {"student_id": student["id"], "exam_no": 1, "score": 88}
    assert_error(teach_client.post(API + "/scores", json=body), 403)


def test_teacher_cannot_create_student(client):
    class_id = create_class(client, "AU-C-7")["id"]
    register_user(client, "teach03", "teach123456", "授课老师丙", role="teacher", class_id=class_id)
    teach_client = make_client("teach03", "teach123456")
    body = {"student_no": "AU-S-6", "class_id": class_id, "name": "x", "birth_date": "2000-01-01", "gender": "男"}
    assert_error(teach_client.post(API + "/students", json=body), 403)


def test_employment_role_any_class(client):
    class_id = create_class(client, "AU-C-8")["id"]
    student = create_student(client, "AU-S-7", class_id)
    register_user(client, "job01", "job123456", "就业专员", role="employment")
    job_client = make_client("job01", "job123456")
    body = {"student_id": student["id"], "company_name": "就业公司", "salary_amount": 10000, "salary_period": "MONTH", "employment_open_date": "2026-01-10"}
    data = ok_data(job_client.post(API + "/employment-records", json=body), 201)
    assert data["company_name"] == "就业公司"


def test_viewer_cannot_write(client):
    class_id = create_class(client, "AU-C-9")["id"]
    register_user(client, "view01", "view123456", "只读用户", role="viewer")
    view_client = make_client("view01", "view123456")
    body = {"student_no": "AU-S-8", "class_id": class_id, "name": "x", "birth_date": "2000-01-01", "gender": "男"}
    assert_error(view_client.post(API + "/students", json=body), 403)


def test_viewer_can_read(client):
    create_class(client, "AU-C-10")
    register_user(client, "view02", "view123456", "只读用户二", role="viewer")
    view_client = make_client("view02", "view123456")
    page = ok_data(view_client.get(API + "/classes"))
    assert page["total"] >= 1


def test_head_teacher_transfer_student_in_own_class(client):
    """班主任给自己班学生转班：目标班也在权限内才允许。"""
    class_a = create_class(client, "AU-C-11A")["id"]
    class_b = create_class(client, "AU-C-11B")["id"]
    student = create_student(client, "AU-S-9", class_a)
    register_user(client, "head04", "head123456", "班主任丁", role="head_teacher", class_id=class_a)
    head_client = make_client("head04", "head123456")
    # 转到自己无权的班：403
    assert_error(head_client.patch(f"{API}/students/{student['id']}", json={"class_id": class_b}), 403)
    # 管理员可以转
    admin_client = client
    data = ok_data(admin_client.patch(f"{API}/students/{student['id']}", json={"class_id": class_b}))
    assert data["class_id"] == class_b
