"""
班级老师关系接口
================
PUT    /api/v1/classes/{class_id}/teachers/{teacher_id}   建立班级老师关系（相同有效关系已存在则直接返回）
GET    /api/v1/classes/{class_id}/teachers                查询班级的老师列表
DELETE /api/v1/classes/{class_id}/teachers/{teacher_id}   解除班级老师关系（逻辑删除）

排班规则（2026-10 修订，3 条铁律）：
1. 一个老师同一时间只能负责一个未结课班级，不管是班主任还是授课老师都一样。
   已结课班级的历史关系不算占用，老师可以去带新班级。
2. 同一个班级里，班主任和授课老师不能是同一人。
3. 一个班级最多只能有一位在任班主任。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, page_data, success
from dao import class_dao, class_teacher_dao, teacher_dao
from database import get_db
from scheme.class_teacher import ClassTeacherItem, ClassTeacherRelationCreate, ClassTeacherRelationRead
from scheme.common import ApiResponse, PageData, RelationType
from scheme.teacher import TeacherRead

router = APIRouter(tags=["班级老师关系"], responses=ERROR_RESPONSES)


@router.put(
    "/classes/{class_id}/teachers/{teacher_id}",
    response_model=ApiResponse[ClassTeacherRelationRead],
    summary="建立班级老师关系（相同的有效关系已存在时直接返回，不重复创建）",
)
def add_class_teacher(
    class_id: int,
    teacher_id: int,
    payload: ClassTeacherRelationCreate,
    db: Session = Depends(get_db),
):
    # 第 1 步：班级和老师都必须存在且未删除
    class_info = class_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")
    if teacher_dao.get_teacher_by_id(db, teacher_id) is None:
        raise HTTPException(status_code=404, detail="老师不存在或已删除")

    # 第 2 步：已结课的班级不能再新增排班（历史关系保留，只能看不能加）
    if class_info.class_status == "已结课":
        raise HTTPException(status_code=409, detail="该班级已结课，不能新增排班")

    # 第 3 步：完全相同的有效关系已经存在，直接返回（PUT 是幂等的，重复调用结果一样）
    relation = class_teacher_dao.get_active_relation(db, class_id, teacher_id, payload.relation_type)
    if relation is not None:
        return success(ClassTeacherRelationRead.model_validate(relation))

    # 第 4 步：铁律 1——老师已经被别的未结课班级占用，不允许再兼任
    busy = class_teacher_dao.get_teacher_busy_relation(db, teacher_id)
    if busy is not None:
        if busy.class_id == class_id:
            # 同一个班级、另一种角色：说明想让班主任再兼授课老师（或反过来），不允许
            raise HTTPException(status_code=409, detail="班主任和授课老师不能是同一人")
        busy_class = class_dao.get_class_by_id(db, busy.class_id)
        busy_no = busy_class.class_no if busy_class else busy.class_id
        raise HTTPException(
            status_code=409,
            detail=f"该老师已负责未结课班级 {busy_no}，一个老师同一时间只能负责一个班级",
        )

    # 第 5 步：铁律 3——班主任角色还要检查这个班是不是已经有班主任了
    if payload.relation_type == "班主任":
        head = class_teacher_dao.get_class_active_head(db, class_id)
        if head is not None:
            raise HTTPException(status_code=409, detail="该班级已有班主任，请先解除原班主任再分配")

    # 第 6 步：都不冲突才新增；以前解除过的关系作为历史记录保留，不去修改它
    data = {"class_id": class_id, "teacher_id": teacher_id, "relation_type": payload.relation_type}
    relation = class_teacher_dao.create_relation(db, data)
    return success(ClassTeacherRelationRead.model_validate(relation))


@router.get(
    "/classes/{class_id}/teachers",
    response_model=ApiResponse[PageData[ClassTeacherItem]],
    summary="查询班级的老师列表（含关系类型）",
)
def list_class_teachers(
    class_id: int,
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    if class_dao.get_class_by_id(db, class_id) is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    rows, total = class_teacher_dao.list_class_teachers(db, class_id, page, page_size)

    # 每一行是 (关系对象, 老师对象)，组装成 ClassTeacherItem
    items = []
    for relation, teacher in rows:
        item = ClassTeacherItem(
            relation_id=relation.id,
            class_id=relation.class_id,
            relation_type=relation.relation_type,
            relation_created_at=relation.created_at,
            teacher=TeacherRead.model_validate(teacher),
        )
        items.append(item)
    return success(page_data(items, total, page, page_size))


@router.delete(
    "/classes/{class_id}/teachers/{teacher_id}",
    status_code=204,
    summary="解除班级老师关系（逻辑删除）",
)
def remove_class_teacher(
    class_id: int,
    teacher_id: int,
    relation_type: RelationType | None = Query(default=None, description="关系类型；不传则解除该老师在此班级的全部关系"),
    db: Session = Depends(get_db),
):
    # 枚举转换成普通字符串
    relation_type_value = None
    if relation_type is not None:
        relation_type_value = relation_type.value

    # 查询要解除的有效关系
    relations = class_teacher_dao.list_active_relations(db, class_id, teacher_id, relation_type_value)
    if len(relations) == 0:
        raise HTTPException(status_code=404, detail="班级老师关系不存在或已解除")

    # 逻辑删除（关系表也只打删除标记，保留历史）
    class_teacher_dao.delete_relations(db, relations)
    return Response(status_code=204)
