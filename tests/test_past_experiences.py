"""过往经历表 student_past_experiences：至少 20 条用例。"""
from tests.helpers import API, assert_error, create_class, create_student, ok_data


def _url(student_id):
    return f"{API}/students/{student_id}/past-experiences"


def _prepare(client, suffix="1"):
    class_id = create_class(client, f"PE-C-{suffix}")["id"]
    return create_student(client, f"PE-S-{suffix}", class_id)["id"]


def test_create_experience_full_fields(client):
    student_id = _prepare(client, "FULL")
    body = {
        "past_salary_amount": 9000,
        "past_salary_period": "MONTH",
        "work_years": 2.5,
        "graduation_date": "2022-06-30",
        "intended_city": "杭州",
        "previous_position": "Python开发工程师",
    }
    data = ok_data(client.post(_url(student_id), json=body), 201)
    assert data["student_id"] == student_id
    assert data["past_salary_amount"] == "9000.00"
    assert data["past_salary_period"] == "MONTH"
    assert data["work_years"] == "2.50"
    assert data["intended_city"] == "杭州"


def test_create_experience_year_salary(client):
    student_id = _prepare(client, "YEAR")
    data = ok_data(client.post(_url(student_id), json={"past_salary_amount": 150000, "past_salary_period": "YEAR"}), 201)
    assert data["past_salary_period"] == "YEAR"


def test_create_multiple_experiences(client):
    student_id = _prepare(client, "MULTI")
    ok_data(client.post(_url(student_id), json={"work_years": 1}), 201)
    ok_data(client.post(_url(student_id), json={"work_years": 2}), 201)
    page = ok_data(client.get(_url(student_id)))
    assert page["total"] == 2


def test_create_experience_amount_without_period(client):
    student_id = _prepare(client, "NOP")
    assert_error(client.post(_url(student_id), json={"past_salary_amount": 9000}), 422)


def test_create_experience_negative_amount(client):
    student_id = _prepare(client, "NEG")
    assert_error(client.post(_url(student_id), json={"past_salary_amount": -1, "past_salary_period": "MONTH"}), 422)


def test_create_experience_negative_years(client):
    student_id = _prepare(client, "NY")
    assert_error(client.post(_url(student_id), json={"work_years": -1}), 422)


def test_create_experience_invalid_period(client):
    student_id = _prepare(client, "IP")
    assert_error(client.post(_url(student_id), json={"past_salary_amount": 9000, "past_salary_period": "WEEK"}), 422)


def test_create_experience_student_not_found(client):
    assert_error(client.post(_url(999999), json={"work_years": 1}), 404)


def test_list_experiences_page_fields(client):
    student_id = _prepare(client, "PAGE")
    ok_data(client.post(_url(student_id), json={"work_years": 1}), 201)
    page = ok_data(client.get(_url(student_id)))
    assert set(page.keys()) == {"items", "total", "page", "page_size"}
    assert page["total"] == 1


def test_list_experiences_student_not_found(client):
    assert_error(client.get(_url(999999)), 404)


def test_get_experience_detail(client):
    student_id = _prepare(client, "DET")
    created = ok_data(client.post(_url(student_id), json={"intended_city": "上海"}), 201)
    data = ok_data(client.get(f"{API}/past-experiences/{created['id']}"))
    assert data["intended_city"] == "上海"
    assert data["student_id"] == student_id


def test_get_experience_not_found(client):
    assert_error(client.get(f"{API}/past-experiences/999999"), 404)


def test_patch_experience_city(client):
    student_id = _prepare(client, "PATCH")
    created = ok_data(client.post(_url(student_id), json={"intended_city": "杭州", "work_years": 1}), 201)
    data = ok_data(client.patch(f"{API}/past-experiences/{created['id']}", json={"intended_city": "深圳"}))
    assert data["intended_city"] == "深圳"
    assert data["work_years"] == "1.00"


def test_patch_experience_clear_period_keep_amount(client):
    student_id = _prepare(client, "CLR")
    created = ok_data(
        client.post(_url(student_id), json={"past_salary_amount": 8000, "past_salary_period": "MONTH"}),
        201,
    )
    assert_error(client.patch(f"{API}/past-experiences/{created['id']}", json={"past_salary_period": None}), 400)


def test_patch_experience_clear_amount_and_period(client):
    student_id = _prepare(client, "CLR2")
    created = ok_data(
        client.post(_url(student_id), json={"past_salary_amount": 8000, "past_salary_period": "MONTH"}),
        201,
    )
    data = ok_data(
        client.patch(
            f"{API}/past-experiences/{created['id']}",
            json={"past_salary_amount": None, "past_salary_period": None},
        )
    )
    assert data["past_salary_amount"] is None
    assert data["past_salary_period"] is None


def test_patch_experience_work_years_null(client):
    student_id = _prepare(client, "WN")
    created = ok_data(client.post(_url(student_id), json={"work_years": 1}), 201)
    assert_error(client.patch(f"{API}/past-experiences/{created['id']}", json={"work_years": None}), 422)


def test_delete_one_experience_keeps_others(client):
    student_id = _prepare(client, "DEL")
    first = ok_data(client.post(_url(student_id), json={"previous_position": "A"}), 201)
    second = ok_data(client.post(_url(student_id), json={"previous_position": "B"}), 201)
    assert client.delete(f"{API}/past-experiences/{first['id']}").status_code == 204
    assert_error(client.get(f"{API}/past-experiences/{first['id']}"), 404)
    page = ok_data(client.get(_url(student_id)))
    assert page["total"] == 1
    assert page["items"][0]["id"] == second["id"]


def test_deleted_experience_not_in_list(client):
    student_id = _prepare(client, "HIDE")
    created = ok_data(client.post(_url(student_id), json={"work_years": 3}), 201)
    client.delete(f"{API}/past-experiences/{created['id']}")
    page = ok_data(client.get(_url(student_id)))
    assert page["total"] == 0


def test_deleted_student_experiences_not_visible(client):
    class_id = create_class(client, "PE-C-DS")["id"]
    student = create_student(client, "PE-S-DS", class_id)
    created = ok_data(client.post(_url(student["id"]), json={"work_years": 1}), 201)
    client.delete(f"{API}/students/{student['id']}")
    assert_error(client.get(f"{API}/past-experiences/{created['id']}"), 404)
    assert_error(client.get(_url(student["id"])), 404)


def test_cannot_add_experience_to_deleted_student(client):
    class_id = create_class(client, "PE-C-ADD")["id"]
    student = create_student(client, "PE-S-ADD", class_id)
    client.delete(f"{API}/students/{student['id']}")
    assert_error(client.post(_url(student["id"]), json={"work_years": 1}), 404)


def test_delete_experience_not_found(client):
    assert_error(client.delete(f"{API}/past-experiences/999999"), 404)


def test_create_experience_default_work_years(client):
    student_id = _prepare(client, "DEF")
    data = ok_data(client.post(_url(student_id), json={}), 201)
    assert data["work_years"] == "0.00"
