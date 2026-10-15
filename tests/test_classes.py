"""班级表 classes：至少 20 条用例。"""
from tests.helpers import API, assert_error, create_class, create_student, create_teacher, ok_data


def test_create_class_success(client):
    data = create_class(client, "C-OK-1")
    assert data["class_no"] == "C-OK-1"
    assert data["completion_date"] is None
    assert data["class_status"] == "在读"
    assert "id" in data


def test_create_class_with_completion_date(client):
    data = create_class(client, "C-OK-2", completion_date="2026-09-30", class_status="已结课")
    assert data["completion_date"] == "2026-09-30"
    assert data["class_status"] == "已结课"


def test_create_class_not_started_status(client):
    data = create_class(client, "C-OK-3", class_status="未开班")
    assert data["class_status"] == "未开班"


def test_create_class_duplicate_no(client):
    create_class(client, "C-DUP-1")
    body = {"class_no": "C-DUP-1", "class_name": "x", "start_date": "2026-03-01"}
    assert_error(client.post(API + "/classes", json=body), 409)


def test_create_class_empty_no(client):
    body = {"class_no": "  ", "class_name": "x", "start_date": "2026-03-01"}
    assert_error(client.post(API + "/classes", json=body), 422)


def test_create_class_missing_name(client):
    body = {"class_no": "C-MISS", "start_date": "2026-03-01"}
    assert_error(client.post(API + "/classes", json=body), 422)


def test_create_class_completion_before_start(client):
    body = {"class_no": "C-DATE-1", "class_name": "x", "start_date": "2026-03-01", "completion_date": "2026-02-01"}
    error = assert_error(client.post(API + "/classes", json=body), 422)
    assert len(error["details"]) > 0


def test_create_class_invalid_status(client):
    body = {"class_no": "C-ST", "class_name": "x", "start_date": "2026-03-01", "class_status": "停办"}
    assert_error(client.post(API + "/classes", json=body), 422)


def test_list_classes_default_page(client):
    create_class(client, "C-LIST-1")
    page = ok_data(client.get(API + "/classes"))
    assert page["page"] == 1
    assert page["page_size"] == 20
    assert page["total"] >= 1
    assert isinstance(page["items"], list)


def test_list_classes_filter_by_no(client):
    create_class(client, "C-FILTER-NO")
    page = ok_data(client.get(API + "/classes", params={"class_no": "C-FILTER-NO"}))
    assert page["total"] == 1
    assert page["items"][0]["class_no"] == "C-FILTER-NO"


def test_list_classes_filter_by_name(client):
    create_class(client, "C-FILTER-NAME", class_name="春季Python班")
    page = ok_data(client.get(API + "/classes", params={"class_name": "Python"}))
    assert page["total"] >= 1


def test_list_classes_filter_by_status(client):
    create_class(client, "C-FILTER-ST", class_status="未开班")
    page = ok_data(client.get(API + "/classes", params={"class_status": "未开班"}))
    assert page["total"] >= 1
    for item in page["items"]:
        assert item["class_status"] == "未开班"


def test_list_classes_page_size_too_large(client):
    assert_error(client.get(API + "/classes", params={"page_size": 101}), 422)


def test_list_classes_page_zero(client):
    assert_error(client.get(API + "/classes", params={"page": 0}), 422)


def test_get_class_detail(client):
    created = create_class(client, "C-DETAIL")
    data = ok_data(client.get(f"{API}/classes/{created['id']}"))
    assert data["id"] == created["id"]
    assert data["class_name"] == created["class_name"]


def test_get_class_not_found(client):
    assert_error(client.get(f"{API}/classes/999999"), 404)


def test_patch_class_name_only(client):
    created = create_class(client, "C-PATCH-1")
    data = ok_data(client.patch(f"{API}/classes/{created['id']}", json={"class_name": "新名称"}))
    assert data["class_name"] == "新名称"
    assert data["start_date"] == "2026-03-01"


def test_patch_class_required_null(client):
    created = create_class(client, "C-PATCH-NULL")
    assert_error(client.patch(f"{API}/classes/{created['id']}", json={"class_name": None}), 422)


def test_patch_class_completion_before_start(client):
    created = create_class(client, "C-PATCH-DATE")
    assert_error(client.patch(f"{API}/classes/{created['id']}", json={"completion_date": "2026-01-01"}), 400)


def test_patch_class_set_completion(client):
    created = create_class(client, "C-PATCH-END")
    data = ok_data(client.patch(f"{API}/classes/{created['id']}", json={"completion_date": "2026-09-30", "class_status": "已结课"}))
    assert data["completion_date"] == "2026-09-30"
    assert data["class_status"] == "已结课"


def test_delete_class_success(client):
    created = create_class(client, "C-DEL-OK")
    assert client.delete(f"{API}/classes/{created['id']}").status_code == 204
    assert_error(client.get(f"{API}/classes/{created['id']}"), 404)


def test_delete_class_not_in_list(client):
    created = create_class(client, "C-DEL-HIDE")
    client.delete(f"{API}/classes/{created['id']}")
    page = ok_data(client.get(API + "/classes", params={"class_no": "C-DEL-HIDE"}))
    assert page["total"] == 0


def test_deleted_class_no_cannot_reuse(client):
    created = create_class(client, "C-DEL-REUSE")
    client.delete(f"{API}/classes/{created['id']}")
    body = {"class_no": "C-DEL-REUSE", "class_name": "x", "start_date": "2026-03-01"}
    assert_error(client.post(API + "/classes", json=body), 409)


def test_delete_class_with_student_conflict(client):
    """班级下有学生时禁止删除，防止产生孤儿数据。"""
    created = create_class(client, "C-DEL-STU")
    create_student(client, "S-KEEP-CLASS", created["id"])
    body = assert_error(client.delete(f"{API}/classes/{created['id']}"), 409)
    assert body["message"] == "该班级下仍有学生，不能删除"


def test_delete_class_with_teacher_conflict(client):
    created = create_class(client, "C-DEL-TEA")
    teacher = create_teacher(client, "T-KEEP-CLASS")
    ok_data(client.put(f"{API}/classes/{created['id']}/teachers/{teacher['id']}", json={"relation_type": "授课老师"}))
    assert_error(client.delete(f"{API}/classes/{created['id']}"), 409)


def test_delete_class_not_found(client):
    assert_error(client.delete(f"{API}/classes/999999"), 404)
