"""统计分析接口：至少 20 条用例，全部排除逻辑删除数据。"""
from tests.helpers import API, assert_error, create_class, create_score, create_student, ok_data, years_ago


def _emp(client, student_id, company, amount, period, open_date=None, offer_date=None):
    body = {
        "student_id": student_id,
        "company_name": company,
        "salary_amount": amount,
        "salary_period": period,
        "employment_open_date": open_date,
        "offer_date": offer_date,
    }
    return ok_data(client.post(API + "/employment-records", json=body), 201)


def test_all_at_least_requires_scores(client):
    class_id = create_class(client, "ST-C-1")["id"]
    a = create_student(client, "ST-A1", class_id)
    b = create_student(client, "ST-B1", class_id, gender="女")
    c = create_student(client, "ST-C1", class_id, gender="女")
    create_score(client, a["id"], 1, 85)
    create_score(client, a["id"], 2, 90)
    create_score(client, b["id"], 1, 79)
    create_score(client, b["id"], 2, 95)
    ids = [item["id"] for item in ok_data(client.get(API + "/statistics/scores/all-at-least"))]
    assert a["id"] in ids
    assert b["id"] not in ids
    assert c["id"] not in ids


def test_all_at_least_custom_threshold(client):
    class_id = create_class(client, "ST-C-2")["id"]
    s = create_student(client, "ST-A2", class_id)
    create_score(client, s["id"], 1, 70)
    ids_80 = [item["id"] for item in ok_data(client.get(API + "/statistics/scores/all-at-least"))]
    ids_60 = [item["id"] for item in ok_data(client.get(API + "/statistics/scores/all-at-least", params={"min_score": 60}))]
    assert s["id"] not in ids_80
    assert s["id"] in ids_60


def test_failures_min_three(client):
    class_id = create_class(client, "ST-C-3")["id"]
    d = create_student(client, "ST-D3", class_id)
    a = create_student(client, "ST-A3", class_id)
    create_score(client, d["id"], 1, 50)
    create_score(client, d["id"], 2, 40)
    create_score(client, d["id"], 3, 30)
    create_score(client, a["id"], 1, 50)
    create_score(client, a["id"], 2, 90)
    failures = ok_data(client.get(API + "/statistics/scores/failures"))
    ids = [item["student_id"] for item in failures]
    assert d["id"] in ids
    assert a["id"] not in ids
    for item in failures:
        if item["student_id"] == d["id"]:
            assert item["fail_count"] == 3
            assert item["class_no"] == "ST-C-3"
            assert item["class_name"] == "ST-C-3 班"


def test_failures_custom_count(client):
    class_id = create_class(client, "ST-C-4")["id"]
    s = create_student(client, "ST-D4", class_id)
    create_score(client, s["id"], 1, 50)
    create_score(client, s["id"], 2, 40)
    data = ok_data(client.get(API + "/statistics/scores/failures", params={"min_fail_count": 2}))
    assert s["id"] in [item["student_id"] for item in data]


def test_class_average_excludes_deleted_student(client):
    class_id = create_class(client, "ST-C-5")["id"]
    a = create_student(client, "ST-A5", class_id)
    e = create_student(client, "ST-E5", class_id)
    create_score(client, a["id"], 1, 80)
    create_score(client, e["id"], 1, 100)
    client.delete(f"{API}/students/{e['id']}")
    averages = ok_data(client.get(API + "/statistics/scores/class-averages", params={"class_id": class_id, "exam_no": 1}))
    assert len(averages) == 1
    assert averages[0]["average_score"] == "80.00"


def test_class_average_three_students(client):
    class_id = create_class(client, "ST-C-6")["id"]
    a = create_student(client, "ST-A6", class_id)
    b = create_student(client, "ST-B6", class_id, gender="女")
    d = create_student(client, "ST-D6", class_id, gender="其他")
    create_score(client, a["id"], 1, 85)
    create_score(client, b["id"], 1, 79)
    create_score(client, d["id"], 1, 50)
    averages = ok_data(client.get(API + "/statistics/scores/class-averages", params={"class_id": class_id, "exam_no": 1}))
    assert averages[0]["average_score"] == "71.33"
    assert averages[0]["sample_count"] == 3


def test_student_counts_gender(client):
    class_id = create_class(client, "ST-C-7")["id"]
    create_student(client, "ST-M7", class_id, gender="男")
    create_student(client, "ST-F7A", class_id, gender="女")
    create_student(client, "ST-F7B", class_id, gender="女")
    create_student(client, "ST-O7", class_id, gender="其他")
    deleted = create_student(client, "ST-DEL7", class_id, gender="男")
    client.delete(f"{API}/students/{deleted['id']}")
    counts = ok_data(client.get(API + "/statistics/classes/student-counts", params={"class_id": class_id}))
    assert counts[0]["total_students"] == 4
    assert counts[0]["male_count"] == 1
    assert counts[0]["female_count"] == 2
    assert counts[0]["other_count"] == 1


def test_student_counts_empty_class(client):
    class_id = create_class(client, "ST-C-8")["id"]
    counts = ok_data(client.get(API + "/statistics/classes/student-counts", params={"class_id": class_id}))
    assert counts[0]["total_students"] == 0


def test_student_counts_class_not_found(client):
    assert_error(client.get(API + "/statistics/classes/student-counts", params={"class_id": 999999}), 404)


def test_over_age_default_30(client):
    class_id = create_class(client, "ST-C-9")["id"]
    older = create_student(client, "ST-OLD9", class_id, birth_date=str(years_ago(35)))
    younger = create_student(client, "ST-YNG9", class_id, birth_date=str(years_ago(25)), gender="女")
    data = ok_data(client.get(API + "/statistics/students/over-age", params={"page_size": 100}))
    nos = [item["student_no"] for item in data["items"]]
    assert older["student_no"] in nos
    assert younger["student_no"] not in nos


def test_over_age_custom_threshold(client):
    class_id = create_class(client, "ST-C-10")["id"]
    create_student(client, "ST-40", class_id, birth_date=str(years_ago(40)))
    create_student(client, "ST-22", class_id, birth_date=str(years_ago(22)), gender="女")
    data = ok_data(client.get(API + "/statistics/students/over-age", params={"age_gt": 35, "page_size": 100}))
    nos = [item["student_no"] for item in data["items"]]
    assert "ST-40" in nos
    assert "ST-22" not in nos


def test_top_salaries_month_beats_year(client):
    class_id = create_class(client, "ST-C-11")["id"]
    a = create_student(client, "ST-A11", class_id)
    b = create_student(client, "ST-B11", class_id, gender="女")
    year_record = _emp(client, b["id"], "年薪公司", 10000000, "YEAR")
    month_record = _emp(client, a["id"], "月薪公司", 900000, "MONTH")
    top = ok_data(client.get(API + "/statistics/employment/top-salaries"))
    assert top[0]["rank"] == 1
    assert top[0]["employment_record_id"] == month_record["id"]
    assert top[0]["salary_period"] == "MONTH"
    assert top[0]["annualized_salary"] == "10800000.00"
    assert top[1]["employment_record_id"] == year_record["id"]


def test_top_salaries_excludes_deleted_student(client):
    class_id = create_class(client, "ST-C-12")["id"]
    e = create_student(client, "ST-E12", class_id)
    _emp(client, e["id"], "已删除学生的公司", 99999999, "YEAR")
    client.delete(f"{API}/students/{e['id']}")
    top = ok_data(client.get(API + "/statistics/employment/top-salaries"))
    assert e["id"] not in [item["student_id"] for item in top]


def test_top_salaries_limit(client):
    class_id = create_class(client, "ST-C-13")["id"]
    s = create_student(client, "ST-A13", class_id)
    for i in range(3):
        _emp(client, s["id"], f"公司{i}", 1000 + i, "YEAR")
    top = ok_data(client.get(API + "/statistics/employment/top-salaries", params={"limit": 2}))
    assert len(top) == 2
    assert top[0]["rank"] == 1
    assert top[1]["rank"] == 2


def test_durations_natural_days(client):
    class_id = create_class(client, "ST-C-14")["id"]
    a = create_student(client, "ST-A14", class_id)
    record = _emp(client, a["id"], "A", 1, "MONTH", "2026-01-10", "2026-02-15")
    items = ok_data(client.get(API + "/statistics/employment/durations", params={"student_id": a["id"]}))
    assert len(items) == 1
    assert items[0]["employment_record_id"] == record["id"]
    assert items[0]["duration_days"] == 36


def test_durations_skip_missing_offer(client):
    class_id = create_class(client, "ST-C-15")["id"]
    a = create_student(client, "ST-A15", class_id)
    _emp(client, a["id"], "无Offer", 1, "MONTH", "2026-04-01", None)
    items = ok_data(client.get(API + "/statistics/employment/durations", params={"student_id": a["id"]}))
    assert items == []


def test_durations_student_not_found(client):
    assert_error(client.get(API + "/statistics/employment/durations", params={"student_id": 999999}), 404)


def test_class_average_duration(client):
    class_data = create_class(client, "ST-C-16")
    a = create_student(client, "ST-A16", class_data["id"])
    b = create_student(client, "ST-B16", class_data["id"], gender="女")
    _emp(client, a["id"], "A", 1, "MONTH", "2026-01-10", "2026-02-15")  # 36
    _emp(client, b["id"], "B", 1, "YEAR", "2026-03-01", "2026-03-21")  # 20
    data = ok_data(client.get(API + "/statistics/employment/class-average-durations", params={"class_id": class_data["id"]}))
    assert len(data) == 1
    assert data[0]["class_no_snapshot"] == "ST-C-16"
    assert data[0]["record_count"] == 2
    assert data[0]["average_duration_days"] == "28.00"


def test_class_average_duration_class_not_found(client):
    assert_error(client.get(API + "/statistics/employment/class-average-durations", params={"class_id": 999999}), 404)


def test_all_at_least_excludes_deleted_score(client):
    class_id = create_class(client, "ST-C-17")["id"]
    s = create_student(client, "ST-A17", class_id)
    create_score(client, s["id"], 1, 90)
    create_score(client, s["id"], 2, 50)
    client.delete(f"{API}/students/{s['id']}/scores/2")
    ids = [item["id"] for item in ok_data(client.get(API + "/statistics/scores/all-at-least"))]
    assert s["id"] in ids


def test_over_age_page_fields(client):
    page = ok_data(client.get(API + "/statistics/students/over-age"))
    assert set(page.keys()) == {"items", "total", "page", "page_size"}


def test_health(client):
    data = ok_data(client.get(API + "/health"))
    assert data["status"] == "ok"


def test_top_salaries_include_education(client):
    """薪资榜要带出学历，前端表格直接展示，不用再查学生档案。"""
    class_id = create_class(client, "ST-C-EDU")["id"]
    s = create_student(client, "ST-EDU", class_id, education="硕士")
    _emp(client, s["id"], "学历公司", 50000000, "YEAR")
    top = ok_data(client.get(API + "/statistics/employment/top-salaries"))
    for item in top:
        if item["student_id"] == s["id"]:
            assert item["education"] == "硕士"
            return
    raise AssertionError("新记录没有进入薪资榜")


def test_class_average_sample_count_single(client):
    """只有一个有效成绩时样本量为 1（已删除学生的成绩不计入）。"""
    class_id = create_class(client, "ST-C-S1")["id"]
    a = create_student(client, "ST-S1A", class_id)
    e = create_student(client, "ST-S1E", class_id)
    create_score(client, a["id"], 1, 80)
    create_score(client, e["id"], 1, 100)
    client.delete(f"{API}/students/{e['id']}")
    averages = ok_data(client.get(API + "/statistics/scores/class-averages", params={"class_id": class_id, "exam_no": 1}))
    assert averages[0]["average_score"] == "80.00"
    assert averages[0]["sample_count"] == 1
