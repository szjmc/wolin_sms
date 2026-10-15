"""老师表 teachers：至少 20 条用例。"""
from tests.helpers import API, assert_error, create_class, create_teacher, ok_data


def test_create_teacher_success(client):
    data = create_teacher(client, "T-OK-1", name="王老师")
    assert data["teacher_no"] == "T-OK-1"
    assert data["name"] == "王老师"
    assert data["contact_info"] is None
    assert data["teacher_status"] == "在职"


def test_create_teacher_with_years_decimal(client):
    data = create_teacher(client, "T-OK-2", teaching_years=5.5)
    assert data["teaching_years"] == "5.50"


def test_create_teacher_with_phone_and_contact(client):
    data = create_teacher(client, "T-OK-3", phone="13800000001", contact_info="微信：wang")
    assert data["phone"] == "13800000001"
    assert data["contact_info"] == "微信：wang"


def test_create_teacher_gender_other(client):
    data = create_teacher(client, "T-OK-4", gender="其他")
    assert data["gender"] == "其他"


def test_create_teacher_negative_years(client):
    body = {"teacher_no": "T-NEG", "name": "x", "teaching_years": -1}
    assert_error(client.post(API + "/teachers", json=body), 422)


def test_create_teacher_duplicate_no(client):
    create_teacher(client, "T-DUP")
    assert_error(client.post(API + "/teachers", json={"teacher_no": "T-DUP", "name": "y"}), 409)


def test_create_teacher_empty_name(client):
    assert_error(client.post(API + "/teachers", json={"teacher_no": "T-EMPTY", "name": ""}), 422)


def test_create_teacher_invalid_gender(client):
    assert_error(client.post(API + "/teachers", json={"teacher_no": "T-G", "name": "x", "gender": "未知"}), 422)


def test_create_teacher_invalid_status(client):
    assert_error(client.post(API + "/teachers", json={"teacher_no": "T-S", "name": "x", "teacher_status": "休假"}), 422)


def test_list_teachers_default(client):
    create_teacher(client, "T-LIST-1")
    page = ok_data(client.get(API + "/teachers"))
    assert page["page"] == 1
    assert page["page_size"] == 20
    assert page["total"] >= 1


def test_list_teachers_filter_no(client):
    create_teacher(client, "T-FILTER-NO")
    page = ok_data(client.get(API + "/teachers", params={"teacher_no": "T-FILTER-NO"}))
    assert page["total"] == 1


def test_list_teachers_filter_name(client):
    create_teacher(client, "T-FILTER-NAME", name="赵敏")
    page = ok_data(client.get(API + "/teachers", params={"name": "赵"}))
    assert page["total"] >= 1


def test_list_teachers_filter_specialty(client):
    create_teacher(client, "T-FILTER-SP", specialty="Python后端")
    page = ok_data(client.get(API + "/teachers", params={"specialty": "Python"}))
    assert page["total"] >= 1


def test_list_teachers_filter_status(client):
    create_teacher(client, "T-FILTER-ST", teacher_status="离职")
    page = ok_data(client.get(API + "/teachers", params={"teacher_status": "离职"}))
    for item in page["items"]:
        assert item["teacher_status"] == "离职"


def test_list_teachers_page_size_limit(client):
    assert_error(client.get(API + "/teachers", params={"page_size": 101}), 422)


def test_get_teacher_detail(client):
    created = create_teacher(client, "T-DETAIL", name="钱老师")
    data = ok_data(client.get(f"{API}/teachers/{created['id']}"))
    assert data["name"] == "钱老师"


def test_get_teacher_not_found(client):
    assert_error(client.get(f"{API}/teachers/999999"), 404)


def test_patch_teacher_contact_and_years(client):
    created = create_teacher(client, "T-PATCH-1")
    data = ok_data(client.patch(f"{API}/teachers/{created['id']}", json={"contact_info": "邮箱 a@b.c", "teaching_years": 8.25}))
    assert data["contact_info"] == "邮箱 a@b.c"
    assert data["teaching_years"] == "8.25"
    assert data["name"] == created["name"]


def test_patch_teacher_required_null(client):
    created = create_teacher(client, "T-PATCH-NULL")
    assert_error(client.patch(f"{API}/teachers/{created['id']}", json={"name": None}), 422)


def test_patch_teacher_negative_years(client):
    created = create_teacher(client, "T-PATCH-NEG")
    assert_error(client.patch(f"{API}/teachers/{created['id']}", json={"teaching_years": -0.1}), 422)


def test_delete_teacher_success(client):
    created = create_teacher(client, "T-DEL-OK")
    assert client.delete(f"{API}/teachers/{created['id']}").status_code == 204
    assert_error(client.get(f"{API}/teachers/{created['id']}"), 404)


def test_deleted_teacher_not_in_list(client):
    created = create_teacher(client, "T-DEL-HIDE")
    client.delete(f"{API}/teachers/{created['id']}")
    page = ok_data(client.get(API + "/teachers", params={"teacher_no": "T-DEL-HIDE"}))
    assert page["total"] == 0


def test_deleted_teacher_no_cannot_reuse(client):
    created = create_teacher(client, "T-DEL-REUSE")
    client.delete(f"{API}/teachers/{created['id']}")
    assert_error(client.post(API + "/teachers", json={"teacher_no": "T-DEL-REUSE", "name": "x"}), 409)


def test_delete_teacher_with_class_relation(client):
    teacher = create_teacher(client, "T-DEL-REL")
    class_data = create_class(client, "C-FOR-TEA")
    ok_data(client.put(f"{API}/classes/{class_data['id']}/teachers/{teacher['id']}", json={"relation_type": "班主任"}))
    assert_error(client.delete(f"{API}/teachers/{teacher['id']}"), 409)


def test_delete_teacher_not_found(client):
    assert_error(client.delete(f"{API}/teachers/999999"), 404)
