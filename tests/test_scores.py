"""成绩表 scores：至少 20 条用例。查改删一律按学生 + 考核序次，不按成绩 id。"""
from tests.helpers import API, assert_error, create_class, create_score, create_student, ok_data


def _prepare(client, suffix="1"):
    class_id = create_class(client, f"SC-C-{suffix}")["id"]
    student = create_student(client, f"SC-S-{suffix}", class_id)
    return student["id"]


def test_create_score_success(client):
    student_id = _prepare(client, "OK")
    data = create_score(client, student_id, 1, 88.5)
    assert data["exam_no"] == 1
    assert data["score"] == "88.50"
    assert data["student_id"] == student_id


def test_create_score_zero_and_hundred(client):
    student_id = _prepare(client, "BOUND")
    zero = create_score(client, student_id, 1, 0)
    hundred = create_score(client, student_id, 2, 100)
    assert zero["score"] == "0.00"
    assert hundred["score"] == "100.00"


def test_create_score_over_100(client):
    student_id = _prepare(client, "OVER")
    assert_error(client.post(API + "/scores", json={"student_id": student_id, "exam_no": 1, "score": 101}), 422)


def test_create_score_negative(client):
    student_id = _prepare(client, "NEG")
    assert_error(client.post(API + "/scores", json={"student_id": student_id, "exam_no": 1, "score": -1}), 422)


def test_create_score_exam_no_zero(client):
    student_id = _prepare(client, "EX0")
    assert_error(client.post(API + "/scores", json={"student_id": student_id, "exam_no": 0, "score": 90}), 422)


def test_create_score_student_not_found(client):
    assert_error(client.post(API + "/scores", json={"student_id": 999999, "exam_no": 1, "score": 90}), 404)


def test_create_score_duplicate_exam(client):
    student_id = _prepare(client, "DUP")
    create_score(client, student_id, 1, 80)
    assert_error(client.post(API + "/scores", json={"student_id": student_id, "exam_no": 1, "score": 70}), 409)


def test_get_score_by_student_and_exam(client):
    student_id = _prepare(client, "GET")
    create_score(client, student_id, 3, 91)
    data = ok_data(client.get(f"{API}/students/{student_id}/scores/3"))
    assert data["exam_no"] == 3
    assert data["score"] == "91.00"
    assert data["student_id"] == student_id


def test_get_score_by_exam_not_found(client):
    student_id = _prepare(client, "GET404")
    assert_error(client.get(f"{API}/students/{student_id}/scores/9"), 404)


def test_get_score_student_not_found(client):
    assert_error(client.get(f"{API}/students/999999/scores/1"), 404)


def test_list_student_scores(client):
    student_id = _prepare(client, "LIST")
    create_score(client, student_id, 1, 70)
    create_score(client, student_id, 2, 80)
    page = ok_data(client.get(f"{API}/students/{student_id}/scores"))
    assert page["total"] == 2
    assert page["items"][0]["exam_no"] == 1
    assert page["items"][1]["exam_no"] == 2


def test_list_student_scores_filter_exam(client):
    student_id = _prepare(client, "LF")
    create_score(client, student_id, 1, 70)
    create_score(client, student_id, 2, 80)
    page = ok_data(client.get(f"{API}/students/{student_id}/scores", params={"exam_no": 2}))
    assert page["total"] == 1
    assert page["items"][0]["exam_no"] == 2


def test_list_scores_student_not_found(client):
    assert_error(client.get(f"{API}/students/999999/scores"), 404)


def test_patch_score_by_student_and_exam(client):
    student_id = _prepare(client, "PATCH")
    create_score(client, student_id, 1, 60)
    data = ok_data(client.patch(f"{API}/students/{student_id}/scores/1", json={"score": 95}))
    assert data["score"] == "95.00"
    assert data["exam_no"] == 1


def test_patch_score_does_not_use_score_id_in_path(client):
    """确认业务改接口路径里是 exam_no，不是成绩主键。"""
    student_id = _prepare(client, "PATH")
    created = create_score(client, student_id, 4, 66)
    # 用成绩 id 去当 exam_no 应该 404（除非碰巧相等）
    if created["id"] != 4:
        assert_error(client.patch(f"{API}/students/{student_id}/scores/{created['id']}", json={"score": 70}), 404)
    data = ok_data(client.patch(f"{API}/students/{student_id}/scores/4", json={"score": 70}))
    assert data["exam_no"] == 4
    assert data["score"] == "70.00"


def test_patch_score_out_of_range(client):
    student_id = _prepare(client, "PR")
    create_score(client, student_id, 1, 60)
    assert_error(client.patch(f"{API}/students/{student_id}/scores/1", json={"score": 120}), 422)


def test_patch_score_missing_body(client):
    student_id = _prepare(client, "PB")
    create_score(client, student_id, 1, 60)
    assert_error(client.patch(f"{API}/students/{student_id}/scores/1", json={}), 422)


def test_patch_score_not_found(client):
    student_id = _prepare(client, "P404")
    assert_error(client.patch(f"{API}/students/{student_id}/scores/8", json={"score": 70}), 404)


def test_delete_score_by_student_and_exam(client):
    student_id = _prepare(client, "DEL")
    create_score(client, student_id, 2, 55)
    assert client.delete(f"{API}/students/{student_id}/scores/2").status_code == 204
    assert_error(client.get(f"{API}/students/{student_id}/scores/2"), 404)


def test_delete_score_then_recreate_same_exam(client):
    student_id = _prepare(client, "RE")
    create_score(client, student_id, 1, 40)
    client.delete(f"{API}/students/{student_id}/scores/1")
    data = create_score(client, student_id, 1, 90)
    assert data["score"] == "90.00"
    page = ok_data(client.get(f"{API}/students/{student_id}/scores"))
    assert page["total"] == 1


def test_deleted_score_not_in_list(client):
    student_id = _prepare(client, "HIDE")
    create_score(client, student_id, 1, 70)
    create_score(client, student_id, 2, 80)
    client.delete(f"{API}/students/{student_id}/scores/1")
    page = ok_data(client.get(f"{API}/students/{student_id}/scores"))
    assert page["total"] == 1
    assert page["items"][0]["exam_no"] == 2


def test_delete_score_student_not_found(client):
    assert_error(client.delete(f"{API}/students/999999/scores/1"), 404)


def test_deleted_student_scores_not_visible(client):
    class_id = create_class(client, "SC-C-DS")["id"]
    student = create_student(client, "SC-S-DS", class_id)
    create_score(client, student["id"], 1, 88)
    client.delete(f"{API}/students/{student['id']}")
    assert_error(client.get(f"{API}/students/{student['id']}/scores/1"), 404)
    assert_error(client.get(f"{API}/students/{student['id']}/scores"), 404)


def test_cannot_add_score_to_deleted_student(client):
    class_id = create_class(client, "SC-C-ADDDEL")["id"]
    student = create_student(client, "SC-S-ADDDEL", class_id)
    client.delete(f"{API}/students/{student['id']}")
    assert_error(client.post(API + "/scores", json={"student_id": student["id"], "exam_no": 1, "score": 90}), 404)
