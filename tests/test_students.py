"""学生表 students：至少 20 条用例。"""
from datetime import timedelta

from tests.helpers import API, TODAY, assert_error, create_class, create_student, ok_data, years_ago


def test_create_student_success(client):
    class_id = create_class(client, "CS-OK")["id"]
    data = create_student(client, "ST-OK-1", class_id, name="张三", hometown="江苏南京")
    assert data["student_no"] == "ST-OK-1"
    assert data["name"] == "张三"
    assert data["hometown"] == "江苏南京"
    assert "age" in data
    assert data.get("age") is not None


def test_create_student_age_matches_birth_date(client):
    class_id = create_class(client, "CS-AGE")["id"]
    data = create_student(client, "ST-AGE-35", class_id, birth_date=str(years_ago(35)))
    assert data["age"] == 35


def test_create_student_age_boundary_tomorrow_birthday(client):
    class_id = create_class(client, "CS-AGE-B")["id"]
    just_31 = create_student(client, "ST-AGE-31", class_id, birth_date=str(years_ago(31)))
    still_30 = create_student(client, "ST-AGE-30", class_id, birth_date=str(years_ago(31, extra_days=1)), gender="女")
    assert just_31["age"] == 31
    assert still_30["age"] == 30


def test_create_student_ignores_client_age(client):
    class_id = create_class(client, "CS-IGN")["id"]
    body = {
        "student_no": "ST-IGN-AGE",
        "class_id": class_id,
        "name": "x",
        "birth_date": str(years_ago(22)),
        "gender": "男",
        "age": 99,
    }
    data = ok_data(client.post(API + "/students", json=body), 201)
    assert data["age"] == 22


def test_create_student_class_not_found(client):
    body = {"student_no": "ST-NO-CLASS", "class_id": 999999, "name": "x", "birth_date": "2000-01-01", "gender": "男"}
    assert_error(client.post(API + "/students", json=body), 404)


def test_create_student_future_birth(client):
    class_id = create_class(client, "CS-FUT")["id"]
    body = {
        "student_no": "ST-FUT",
        "class_id": class_id,
        "name": "x",
        "birth_date": str(TODAY + timedelta(days=1)),
        "gender": "男",
    }
    assert_error(client.post(API + "/students", json=body), 422)


def test_create_student_training_date_order(client):
    class_id = create_class(client, "CS-TR")["id"]
    body = {
        "student_no": "ST-TR",
        "class_id": class_id,
        "name": "x",
        "birth_date": "2000-01-01",
        "gender": "男",
        "training_enrollment_date": "2026-03-01",
        "training_graduation_date": "2026-02-01",
    }
    assert_error(client.post(API + "/students", json=body), 422)


def test_create_student_invalid_gender(client):
    class_id = create_class(client, "CS-G")["id"]
    body = {"student_no": "ST-G", "class_id": class_id, "name": "x", "birth_date": "2000-01-01", "gender": "未知"}
    assert_error(client.post(API + "/students", json=body), 422)


def test_create_student_duplicate_no(client):
    class_id = create_class(client, "CS-DUP")["id"]
    create_student(client, "ST-DUP", class_id)
    body = {"student_no": "ST-DUP", "class_id": class_id, "name": "y", "birth_date": "2000-01-01", "gender": "女"}
    assert_error(client.post(API + "/students", json=body), 409)


def test_create_student_missing_student_no(client):
    class_id = create_class(client, "CS-MISS")["id"]
    body = {"class_id": class_id, "name": "x", "birth_date": "2000-01-01", "gender": "男"}
    assert_error(client.post(API + "/students", json=body), 422)


def test_list_students_filter_no_and_gender(client):
    class_id = create_class(client, "CS-LIST")["id"]
    create_student(client, "ST-LIST-M", class_id, gender="男")
    create_student(client, "ST-LIST-F", class_id, gender="女")
    page = ok_data(client.get(API + "/students", params={"class_id": class_id, "gender": "女"}))
    assert page["total"] == 1
    assert page["items"][0]["gender"] == "女"


def test_list_students_filter_name(client):
    class_id = create_class(client, "CS-NAME")["id"]
    create_student(client, "ST-NAME-1", class_id, name="李雷")
    page = ok_data(client.get(API + "/students", params={"name": "李"}))
    assert page["total"] >= 1


def test_list_students_age_gt(client):
    class_id = create_class(client, "CS-AGEGT")["id"]
    create_student(client, "ST-GT-35", class_id, birth_date=str(years_ago(35)))
    create_student(client, "ST-GT-20", class_id, birth_date=str(years_ago(20)), gender="女")
    page = ok_data(client.get(API + "/students", params={"class_id": class_id, "age_gt": 30}))
    nos = [item["student_no"] for item in page["items"]]
    assert "ST-GT-35" in nos
    assert "ST-GT-20" not in nos


def test_list_students_page_fields(client):
    page = ok_data(client.get(API + "/students"))
    assert set(page.keys()) == {"items", "total", "page", "page_size"}


def test_get_student_detail(client):
    class_id = create_class(client, "CS-DET")["id"]
    created = create_student(client, "ST-DET", class_id, name="韩梅梅")
    data = ok_data(client.get(f"{API}/students/{created['id']}"))
    assert data["name"] == "韩梅梅"
    assert data["age"] == created["age"]


def test_get_student_not_found(client):
    assert_error(client.get(f"{API}/students/999999"), 404)


def test_patch_student_training_dates(client):
    class_id = create_class(client, "CS-PATCH")["id"]
    created = create_student(client, "ST-PATCH", class_id, training_graduation_date=None)
    ok_data(client.patch(f"{API}/students/{created['id']}", json={"training_enrollment_date": "2026-03-01"}))
    data = ok_data(client.patch(f"{API}/students/{created['id']}", json={"training_graduation_date": "2026-10-01"}))
    assert data["training_enrollment_date"] == "2026-03-01"
    assert data["training_graduation_date"] == "2026-10-01"
    assert data["name"] == created["name"]


def test_patch_student_training_order_invalid(client):
    class_id = create_class(client, "CS-PATCH-D")["id"]
    created = create_student(client, "ST-PATCH-D", class_id, training_enrollment_date="2026-03-01", training_graduation_date=None)
    assert_error(client.patch(f"{API}/students/{created['id']}", json={"training_graduation_date": "2026-01-01"}), 400)


def test_patch_student_required_null(client):
    class_id = create_class(client, "CS-NULL")["id"]
    created = create_student(client, "ST-NULL", class_id)
    assert_error(client.patch(f"{API}/students/{created['id']}", json={"name": None}), 422)


def test_patch_student_clear_optional(client):
    class_id = create_class(client, "CS-CLR")["id"]
    created = create_student(client, "ST-CLR", class_id, hometown="南京")
    data = ok_data(client.patch(f"{API}/students/{created['id']}", json={"hometown": None}))
    assert data["hometown"] is None


def test_patch_student_new_class_not_found(client):
    class_id = create_class(client, "CS-NC")["id"]
    created = create_student(client, "ST-NC", class_id)
    assert_error(client.patch(f"{API}/students/{created['id']}", json={"class_id": 999999}), 404)


def test_patch_student_future_birth(client):
    class_id = create_class(client, "CS-FB")["id"]
    created = create_student(client, "ST-FB", class_id)
    assert_error(client.patch(f"{API}/students/{created['id']}", json={"birth_date": str(TODAY + timedelta(days=2))}), 422)


def test_delete_student_hides_from_list(client):
    class_id = create_class(client, "CS-DEL")["id"]
    created = create_student(client, "ST-DEL", class_id)
    assert client.delete(f"{API}/students/{created['id']}").status_code == 204
    assert_error(client.get(f"{API}/students/{created['id']}"), 404)
    page = ok_data(client.get(API + "/students", params={"student_no": "ST-DEL"}))
    assert page["total"] == 0


def test_deleted_student_no_cannot_reuse(client):
    class_id = create_class(client, "CS-REUSE")["id"]
    created = create_student(client, "ST-REUSE", class_id)
    client.delete(f"{API}/students/{created['id']}")
    body = {"student_no": "ST-REUSE", "class_id": class_id, "name": "y", "birth_date": "2000-01-01", "gender": "男"}
    assert_error(client.post(API + "/students", json=body), 409)


def test_delete_student_not_found(client):
    assert_error(client.delete(f"{API}/students/999999"), 404)
