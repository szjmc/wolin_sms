"""就业记录表 employment_records：至少 20 条用例。"""
from tests.helpers import API, assert_error, create_class, create_student, ok_data


def _create_emp(client, student_id, company, amount, period, **extra):
    body = {"student_id": student_id, "company_name": company, "salary_amount": amount, "salary_period": period}
    body.update(extra)
    return ok_data(client.post(API + "/employment-records", json=body), 201)


def test_create_employment_month_annualized(client):
    class_data = create_class(client, "EM-C-1")
    student = create_student(client, "EM-S-1", class_data["id"], name="张三")
    data = _create_emp(
        client, student["id"], "示例科技有限公司", 15000, "MONTH",
        employment_open_date="2026-01-10", offer_date="2026-02-15",
        employment_city="杭州", position="后端开发工程师",
    )
    assert data["salary_amount"] == "15000.00"
    assert data["salary_period"] == "MONTH"
    assert data["annualized_salary"] == "180000.00"
    assert data["student_name_snapshot"] == "张三"
    assert data["class_no_snapshot"] == "EM-C-1"
    assert data["employment_city"] == "杭州"
    assert data["position"] == "后端开发工程师"


def test_create_employment_year_annualized(client):
    class_id = create_class(client, "EM-C-2")["id"]
    student = create_student(client, "EM-S-2", class_id)
    data = _create_emp(client, student["id"], "年薪公司", 200000, "YEAR")
    assert data["annualized_salary"] == "200000.00"


def test_create_multiple_records_same_student(client):
    class_id = create_class(client, "EM-C-3")["id"]
    student = create_student(client, "EM-S-3", class_id)
    first = _create_emp(client, student["id"], "公司A", 10000, "MONTH", employment_open_date="2026-01-01")
    second = _create_emp(client, student["id"], "公司B", 20000, "MONTH", employment_open_date="2026-05-01")
    page = ok_data(client.get(f"{API}/students/{student['id']}/employment-records"))
    assert page["total"] == 2
    assert page["items"][0]["id"] == first["id"]
    assert page["items"][1]["id"] == second["id"]


def test_create_employment_offer_before_open(client):
    class_id = create_class(client, "EM-C-4")["id"]
    student = create_student(client, "EM-S-4", class_id)
    body = {
        "student_id": student["id"], "company_name": "A", "salary_amount": 10000, "salary_period": "MONTH",
        "employment_open_date": "2026-02-01", "offer_date": "2026-01-01",
    }
    assert_error(client.post(API + "/employment-records", json=body), 422)


def test_create_employment_invalid_period(client):
    class_id = create_class(client, "EM-C-5")["id"]
    student = create_student(client, "EM-S-5", class_id)
    body = {"student_id": student["id"], "company_name": "A", "salary_amount": 10000, "salary_period": "WEEK"}
    assert_error(client.post(API + "/employment-records", json=body), 422)


def test_create_employment_negative_salary(client):
    class_id = create_class(client, "EM-C-6")["id"]
    student = create_student(client, "EM-S-6", class_id)
    body = {"student_id": student["id"], "company_name": "A", "salary_amount": -1, "salary_period": "MONTH"}
    assert_error(client.post(API + "/employment-records", json=body), 422)


def test_create_employment_student_not_found(client):
    body = {"student_id": 999999, "company_name": "A", "salary_amount": 1, "salary_period": "MONTH"}
    assert_error(client.post(API + "/employment-records", json=body), 404)


def test_create_employment_missing_company(client):
    class_id = create_class(client, "EM-C-7")["id"]
    student = create_student(client, "EM-S-7", class_id)
    body = {"student_id": student["id"], "salary_amount": 1, "salary_period": "MONTH"}
    assert_error(client.post(API + "/employment-records", json=body), 422)


def test_list_filter_city_and_student_no(client):
    class_id = create_class(client, "EM-C-8")["id"]
    student = create_student(client, "EM-S-8", class_id)
    _create_emp(client, student["id"], "杭司", 10000, "MONTH", employment_city="杭州")
    _create_emp(client, student["id"], "沪司", 10000, "MONTH", employment_city="上海")
    page = ok_data(client.get(API + "/employment-records", params={"employment_city": "杭州", "student_no": "EM-S-8"}))
    assert page["total"] == 1
    assert page["items"][0]["employment_city"] == "杭州"


def test_list_filter_position(client):
    class_id = create_class(client, "EM-C-9")["id"]
    student = create_student(client, "EM-S-9", class_id)
    _create_emp(client, student["id"], "A", 1, "MONTH", position="数据分析师")
    page = ok_data(client.get(API + "/employment-records", params={"position": "数据", "student_no": "EM-S-9"}))
    assert page["total"] == 1


def test_list_filter_min_annualized(client):
    class_id = create_class(client, "EM-C-10")["id"]
    student = create_student(client, "EM-S-10", class_id)
    _create_emp(client, student["id"], "低", 10000, "MONTH")
    high = _create_emp(client, student["id"], "高", 200000, "YEAR")
    page = ok_data(client.get(API + "/employment-records", params={"min_annualized_salary": 190000, "student_no": "EM-S-10"}))
    assert page["total"] == 1
    assert page["items"][0]["id"] == high["id"]


def test_list_filter_raw_salary_with_period(client):
    class_id = create_class(client, "EM-C-11")["id"]
    student = create_student(client, "EM-S-11", class_id)
    month = _create_emp(client, student["id"], "月", 15000, "MONTH")
    _create_emp(client, student["id"], "年", 15000, "YEAR")
    page = ok_data(client.get(API + "/employment-records", params={"salary_period": "MONTH", "min_salary": 10000, "student_no": "EM-S-11"}))
    assert page["total"] == 1
    assert page["items"][0]["id"] == month["id"]


def test_list_by_class_snapshot(client):
    class_data = create_class(client, "EM-C-12")
    student = create_student(client, "EM-S-12", class_data["id"])
    _create_emp(client, student["id"], "A", 1, "MONTH")
    page = ok_data(client.get(f"{API}/classes/{class_data['id']}/employment-records"))
    assert page["total"] == 1
    assert page["items"][0]["class_no_snapshot"] == "EM-C-12"


def test_snapshot_not_changed_after_rename(client):
    class_id = create_class(client, "EM-C-13")["id"]
    student = create_student(client, "EM-S-13", class_id, name="张三")
    record = _create_emp(client, student["id"], "A", 1, "MONTH")
    ok_data(client.patch(f"{API}/students/{student['id']}", json={"name": "张三丰"}))
    data = ok_data(client.get(f"{API}/employment-records/{record['id']}"))
    assert data["student_name_snapshot"] == "张三"


def test_get_employment_detail(client):
    class_id = create_class(client, "EM-C-14")["id"]
    student = create_student(client, "EM-S-14", class_id)
    record = _create_emp(client, student["id"], "详司", 8000, "MONTH")
    data = ok_data(client.get(f"{API}/employment-records/{record['id']}"))
    assert data["company_name"] == "详司"
    assert data["annualized_salary"] == "96000.00"


def test_get_employment_not_found(client):
    assert_error(client.get(f"{API}/employment-records/999999"), 404)


def test_patch_one_record_does_not_touch_others(client):
    class_id = create_class(client, "EM-C-15")["id"]
    student = create_student(client, "EM-S-15", class_id)
    first = _create_emp(client, student["id"], "公司A", 1, "MONTH")
    second = _create_emp(client, student["id"], "公司B", 2, "YEAR")
    data = ok_data(client.patch(f"{API}/employment-records/{first['id']}", json={"company_name": "改名后的公司"}))
    assert data["company_name"] == "改名后的公司"
    assert ok_data(client.get(f"{API}/employment-records/{second['id']}"))["company_name"] == "公司B"


def test_patch_offer_before_open(client):
    class_id = create_class(client, "EM-C-16")["id"]
    student = create_student(client, "EM-S-16", class_id)
    record = _create_emp(client, student["id"], "A", 1, "MONTH", employment_open_date="2026-02-01", offer_date="2026-03-01")
    assert_error(client.patch(f"{API}/employment-records/{record['id']}", json={"offer_date": "2025-12-31"}), 400)


def test_patch_required_null(client):
    class_id = create_class(client, "EM-C-17")["id"]
    student = create_student(client, "EM-S-17", class_id)
    record = _create_emp(client, student["id"], "A", 1, "MONTH")
    assert_error(client.patch(f"{API}/employment-records/{record['id']}", json={"company_name": None}), 422)


def test_delete_one_keeps_other(client):
    class_id = create_class(client, "EM-C-18")["id"]
    student = create_student(client, "EM-S-18", class_id)
    first = _create_emp(client, student["id"], "A", 1, "MONTH")
    second = _create_emp(client, student["id"], "B", 2, "MONTH")
    assert client.delete(f"{API}/employment-records/{first['id']}").status_code == 204
    page = ok_data(client.get(f"{API}/students/{student['id']}/employment-records"))
    assert page["total"] == 1
    assert page["items"][0]["id"] == second["id"]


def test_deleted_student_employment_not_visible(client):
    class_id = create_class(client, "EM-C-19")["id"]
    student = create_student(client, "EM-S-19", class_id)
    record = _create_emp(client, student["id"], "A", 1, "MONTH")
    client.delete(f"{API}/students/{student['id']}")
    assert_error(client.get(f"{API}/employment-records/{record['id']}"), 404)
    page = ok_data(client.get(API + "/employment-records", params={"student_no": "EM-S-19"}))
    assert page["total"] == 0


def test_cannot_add_employment_to_deleted_student(client):
    class_id = create_class(client, "EM-C-20")["id"]
    student = create_student(client, "EM-S-20", class_id)
    client.delete(f"{API}/students/{student['id']}")
    body = {"student_id": student["id"], "company_name": "A", "salary_amount": 1, "salary_period": "MONTH"}
    assert_error(client.post(API + "/employment-records", json=body), 404)


def test_list_class_not_found(client):
    assert_error(client.get(f"{API}/classes/999999/employment-records"), 404)


def test_offer_without_open_date_rejected(client):
    """就业尚未开放就填 Offer 日期，必须拒绝。"""
    class_id = create_class(client, "EM-C-21A")["id"]
    student = create_student(client, "EM-S-21A", class_id)
    body = {"student_id": student["id"], "company_name": "A", "salary_amount": 10000, "salary_period": "MONTH", "offer_date": "2026-03-01"}
    assert_error(client.post(API + "/employment-records", json=body), 422)


def test_patch_offer_without_open_date_rejected(client):
    """修改时也要拦：已有 Offer 时不能只清空就业开放日期。"""
    class_id = create_class(client, "EM-C-21B")["id"]
    student = create_student(client, "EM-S-21B", class_id)
    record = _create_emp(client, student["id"], "A", 10000, "MONTH", employment_open_date="2026-01-01", offer_date="2026-02-01")
    error = assert_error(client.patch(f"{API}/employment-records/{record['id']}", json={"employment_open_date": None}), 400)
    assert "尚未开放" in error["message"]


def test_offer_same_day_as_open_allowed(client):
    """Offer 和开放日期同一天可以保存。"""
    class_id = create_class(client, "EM-C-21C")["id"]
    student = create_student(client, "EM-S-21C", class_id)
    data = _create_emp(client, student["id"], "A", 10000, "MONTH", employment_open_date="2026-02-01", offer_date="2026-02-01")
    assert data["employment_open_date"] == "2026-02-01"
    assert data["offer_date"] == "2026-02-01"


def test_zero_salary_allowed(client):
    class_id = create_class(client, "EM-C-21")["id"]
    student = create_student(client, "EM-S-21", class_id)
    data = _create_emp(client, student["id"], "实习", 0, "MONTH")
    assert data["salary_amount"] == "0.00"
    assert data["annualized_salary"] == "0.00"
