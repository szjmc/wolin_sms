"""
班级老师关系表 class_teacher_relations：新版排班规则测试。

3 条铁律：
1. 一个老师同一时间只能负责一个未结课班级（班主任、授课老师都一样）
2. 同一个班级里，班主任和授课老师不能是同一人
3. 一个班级最多只能有一位在任班主任
"""
from tests.helpers import API, assert_error, create_class, create_teacher, ok_data


def _put(client, class_id, teacher_id, relation_type="授课老师"):
    return ok_data(client.put(f"{API}/classes/{class_id}/teachers/{teacher_id}", json={"relation_type": relation_type}))


def test_create_relation_head_teacher(client):
    class_id = create_class(client, "CT-C-1")["id"]
    teacher_id = create_teacher(client, "CT-T-1")["id"]
    data = _put(client, class_id, teacher_id, "班主任")
    assert data["class_id"] == class_id
    assert data["teacher_id"] == teacher_id
    assert data["relation_type"] == "班主任"


def test_create_relation_lecturer_default(client):
    class_id = create_class(client, "CT-C-2")["id"]
    teacher_id = create_teacher(client, "CT-T-2")["id"]
    data = ok_data(client.put(f"{API}/classes/{class_id}/teachers/{teacher_id}", json={}))
    assert data["relation_type"] == "授课老师"


def test_put_same_relation_is_idempotent(client):
    class_id = create_class(client, "CT-C-3")["id"]
    teacher_id = create_teacher(client, "CT-T-3")["id"]
    first = _put(client, class_id, teacher_id, "班主任")
    again = _put(client, class_id, teacher_id, "班主任")
    assert first["id"] == again["id"]
    page = ok_data(client.get(f"{API}/classes/{class_id}/teachers"))
    assert page["total"] == 1


def test_same_teacher_two_roles_rejected(client):
    """铁律 2：同一人不能又当班主任又当授课老师。"""
    class_id = create_class(client, "CT-C-4")["id"]
    teacher_id = create_teacher(client, "CT-T-4")["id"]
    _put(client, class_id, teacher_id, "班主任")
    body = assert_error(
        client.put(f"{API}/classes/{class_id}/teachers/{teacher_id}", json={"relation_type": "授课老师"}),
        409,
    )
    assert "不能是同一人" in body["message"]


def test_teacher_cannot_serve_two_classes(client):
    """铁律 1：老师已负责 A 班，不能再去 B 班（不管什么角色）。"""
    class_a = create_class(client, "CT-C-4A")["id"]
    class_b = create_class(client, "CT-C-4B")["id"]
    teacher_id = create_teacher(client, "CT-T-4X")["id"]
    _put(client, class_a, teacher_id, "班主任")
    assert_error(
        client.put(f"{API}/classes/{class_b}/teachers/{teacher_id}", json={"relation_type": "授课老师"}),
        409,
    )
    assert_error(
        client.put(f"{API}/classes/{class_b}/teachers/{teacher_id}", json={"relation_type": "班主任"}),
        409,
    )


def test_lecturer_cannot_serve_two_classes(client):
    """铁律 1 同样约束授课老师：授课老师也只负责一个班级。"""
    class_a = create_class(client, "CT-C-4C")["id"]
    class_b = create_class(client, "CT-C-4D")["id"]
    teacher_id = create_teacher(client, "CT-T-4Y")["id"]
    _put(client, class_a, teacher_id, "授课老师")
    assert_error(
        client.put(f"{API}/classes/{class_b}/teachers/{teacher_id}", json={"relation_type": "授课老师"}),
        409,
    )


def test_class_cannot_have_two_heads(client):
    """铁律 3：一个班只能有一位在任班主任。"""
    class_id = create_class(client, "CT-C-4E")["id"]
    t1 = create_teacher(client, "CT-T-4H1")["id"]
    t2 = create_teacher(client, "CT-T-4H2")["id"]
    _put(client, class_id, t1, "班主任")
    assert_error(
        client.put(f"{API}/classes/{class_id}/teachers/{t2}", json={"relation_type": "班主任"}),
        409,
    )


def test_teacher_can_move_after_unlink(client):
    """解除原关系后，老师可以去带新班级。"""
    class_a = create_class(client, "CT-C-4F")["id"]
    class_b = create_class(client, "CT-C-4G")["id"]
    teacher_id = create_teacher(client, "CT-T-4Z")["id"]
    _put(client, class_a, teacher_id, "班主任")
    assert client.delete(f"{API}/classes/{class_a}/teachers/{teacher_id}").status_code == 204
    data = _put(client, class_b, teacher_id, "授课老师")
    assert data["class_id"] == class_b


def test_finished_class_frees_teacher(client):
    """班级结课后，历史关系保留，但老师不再被占用，可以带新班。"""
    class_a = create_class(client, "CT-C-4H")["id"]
    class_b = create_class(client, "CT-C-4I")["id"]
    teacher_id = create_teacher(client, "CT-T-4W")["id"]
    _put(client, class_a, teacher_id, "班主任")
    ok_data(client.patch(f"{API}/classes/{class_a}", json={"class_status": "已结课"}))
    data = _put(client, class_b, teacher_id, "班主任")
    assert data["class_id"] == class_b


def test_cannot_assign_to_finished_class(client):
    """已结课的班级不能新增排班。"""
    class_id = create_class(client, "CT-C-4J", class_status="已结课")["id"]
    teacher_id = create_teacher(client, "CT-T-4V")["id"]
    assert_error(
        client.put(f"{API}/classes/{class_id}/teachers/{teacher_id}", json={"relation_type": "授课老师"}),
        409,
    )


def test_invalid_relation_type(client):
    class_id = create_class(client, "CT-C-5")["id"]
    teacher_id = create_teacher(client, "CT-T-5")["id"]
    assert_error(client.put(f"{API}/classes/{class_id}/teachers/{teacher_id}", json={"relation_type": "校长"}), 422)


def test_class_not_found(client):
    teacher_id = create_teacher(client, "CT-T-6")["id"]
    assert_error(client.put(f"{API}/classes/999999/teachers/{teacher_id}", json={"relation_type": "授课老师"}), 404)


def test_teacher_not_found(client):
    class_id = create_class(client, "CT-C-7")["id"]
    assert_error(client.put(f"{API}/classes/{class_id}/teachers/999999", json={"relation_type": "授课老师"}), 404)


def test_list_class_teachers_contains_teacher(client):
    class_id = create_class(client, "CT-C-8")["id"]
    teacher = create_teacher(client, "CT-T-8", name="赵老师")
    _put(client, class_id, teacher["id"], "班主任")
    page = ok_data(client.get(f"{API}/classes/{class_id}/teachers"))
    assert page["total"] == 1
    assert page["items"][0]["teacher"]["name"] == "赵老师"
    assert page["items"][0]["relation_type"] == "班主任"


def test_list_class_teachers_page_fields(client):
    class_id = create_class(client, "CT-C-9")["id"]
    page = ok_data(client.get(f"{API}/classes/{class_id}/teachers"))
    assert page["total"] == 0
    assert page["page"] == 1
    assert page["page_size"] == 20


def test_list_class_not_found(client):
    assert_error(client.get(f"{API}/classes/999999/teachers"), 404)


def test_delete_head_keeps_lecturer(client):
    """班主任和授课老师是两个人时，解除班主任不影响授课老师。"""
    class_id = create_class(client, "CT-C-10")["id"]
    head_id = create_teacher(client, "CT-T-10H")["id"]
    lecturer_id = create_teacher(client, "CT-T-10L")["id"]
    _put(client, class_id, head_id, "班主任")
    _put(client, class_id, lecturer_id, "授课老师")
    url = f"{API}/classes/{class_id}/teachers/{head_id}"
    assert client.delete(url, params={"relation_type": "班主任"}).status_code == 204
    page = ok_data(client.get(f"{API}/classes/{class_id}/teachers"))
    assert page["total"] == 1
    assert page["items"][0]["relation_type"] == "授课老师"


def test_delete_without_type_removes_that_teacher_only(client):
    """不传角色时只解除这个老师的关系，不影响班里其他老师。"""
    class_id = create_class(client, "CT-C-11")["id"]
    head_id = create_teacher(client, "CT-T-11H")["id"]
    lecturer_id = create_teacher(client, "CT-T-11L")["id"]
    _put(client, class_id, head_id, "班主任")
    _put(client, class_id, lecturer_id, "授课老师")
    assert client.delete(f"{API}/classes/{class_id}/teachers/{head_id}").status_code == 204
    page = ok_data(client.get(f"{API}/classes/{class_id}/teachers"))
    assert page["total"] == 1
    assert page["items"][0]["teacher"]["teacher_no"] == "CT-T-11L"


def test_delete_missing_relation_404(client):
    class_id = create_class(client, "CT-C-12")["id"]
    teacher_id = create_teacher(client, "CT-T-12")["id"]
    assert_error(client.delete(f"{API}/classes/{class_id}/teachers/{teacher_id}"), 404)


def test_deleted_relation_hidden_from_list(client):
    class_id = create_class(client, "CT-C-13")["id"]
    teacher_id = create_teacher(client, "CT-T-13")["id"]
    _put(client, class_id, teacher_id, "授课老师")
    client.delete(f"{API}/classes/{class_id}/teachers/{teacher_id}")
    page = ok_data(client.get(f"{API}/classes/{class_id}/teachers"))
    assert page["total"] == 0


def test_recreate_after_delete_creates_new_row(client):
    class_id = create_class(client, "CT-C-14")["id"]
    teacher_id = create_teacher(client, "CT-T-14")["id"]
    first = _put(client, class_id, teacher_id, "授课老师")
    client.delete(f"{API}/classes/{class_id}/teachers/{teacher_id}", params={"relation_type": "授课老师"})
    second = _put(client, class_id, teacher_id, "授课老师")
    assert second["id"] != first["id"]


def test_cannot_delete_class_while_relation_exists(client):
    class_id = create_class(client, "CT-C-15")["id"]
    teacher_id = create_teacher(client, "CT-T-15")["id"]
    _put(client, class_id, teacher_id, "授课老师")
    assert_error(client.delete(f"{API}/classes/{class_id}"), 409)


def test_cannot_delete_teacher_while_relation_exists(client):
    class_id = create_class(client, "CT-C-16")["id"]
    teacher_id = create_teacher(client, "CT-T-16")["id"]
    _put(client, class_id, teacher_id, "班主任")
    assert_error(client.delete(f"{API}/teachers/{teacher_id}"), 409)


def test_can_delete_after_unlinking(client):
    class_id = create_class(client, "CT-C-17")["id"]
    teacher_id = create_teacher(client, "CT-T-17")["id"]
    _put(client, class_id, teacher_id, "授课老师")
    client.delete(f"{API}/classes/{class_id}/teachers/{teacher_id}")
    assert client.delete(f"{API}/teachers/{teacher_id}").status_code == 204
    assert client.delete(f"{API}/classes/{class_id}").status_code == 204


def test_deleted_teacher_not_listed_in_class(client):
    """老师被删除前必须先解除关系；解除后列表为空。"""
    class_id = create_class(client, "CT-C-18")["id"]
    teacher_id = create_teacher(client, "CT-T-18")["id"]
    _put(client, class_id, teacher_id, "授课老师")
    client.delete(f"{API}/classes/{class_id}/teachers/{teacher_id}")
    page = ok_data(client.get(f"{API}/classes/{class_id}/teachers"))
    assert page["total"] == 0


def test_two_teachers_same_class(client):
    class_id = create_class(client, "CT-C-19")["id"]
    t1 = create_teacher(client, "CT-T-19A")["id"]
    t2 = create_teacher(client, "CT-T-19B")["id"]
    _put(client, class_id, t1, "班主任")
    _put(client, class_id, t2, "授课老师")
    page = ok_data(client.get(f"{API}/classes/{class_id}/teachers"))
    assert page["total"] == 2


def test_list_page_size_limit(client):
    class_id = create_class(client, "CT-C-20")["id"]
    assert_error(client.get(f"{API}/classes/{class_id}/teachers", params={"page_size": 101}), 422)
