"""
测试辅助函数：创建基础数据、断言统一响应格式。
"""
from datetime import date, timedelta


API = "/api/v1"
TODAY = date.today()


def years_ago(years, extra_days=0):
    """返回「今天往前推 years 年，再往后加 extra_days 天」的日期。"""
    target_year = TODAY.year - years
    if TODAY.month == 2 and TODAY.day == 29:
        base_date = date(target_year, 2, 28)
    else:
        base_date = date(target_year, TODAY.month, TODAY.day)
    return base_date + timedelta(days=extra_days)


def ok_data(response, expected_status=200):
    """断言成功响应（code=0），返回 data。"""
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == 0
    assert body["message"] == "success"
    return body["data"]


def assert_error(response, expected_status):
    """断言失败响应，业务码 = HTTP 状态码 × 100 + 1。"""
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["code"] == expected_status * 100 + 1
    return body


def create_class(client, class_no, **extra):
    """快捷新增班级，返回 data。"""
    body = {"class_no": class_no, "class_name": class_no + " 班", "start_date": "2026-03-01"}
    body.update(extra)
    return ok_data(client.post(API + "/classes", json=body), 201)


def create_teacher(client, teacher_no, **extra):
    """快捷新增老师，返回 data。"""
    body = {"teacher_no": teacher_no, "name": "老师" + teacher_no}
    body.update(extra)
    return ok_data(client.post(API + "/teachers", json=body), 201)


def create_student(client, student_no, class_id, **extra):
    """快捷新增学生，返回 data。"""
    body = {
        "student_no": student_no,
        "class_id": class_id,
        "name": extra.pop("name", "学生" + student_no),
        "birth_date": extra.pop("birth_date", "2000-01-01"),
        "gender": extra.pop("gender", "男"),
    }
    body.update(extra)
    return ok_data(client.post(API + "/students", json=body), 201)


def create_score(client, student_id, exam_no, score):
    """快捷新增成绩，返回 data。"""
    body = {"student_id": student_id, "exam_no": exam_no, "score": score}
    return ok_data(client.post(API + "/scores", json=body), 201)
