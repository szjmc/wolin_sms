"""班级—老师关系（排班）接口。"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, page_data, success
from database import get_db
from dao import class_info_dao, class_teacher_dao
from dao import teacher as teacher_dao
from scheme.class_teacher import (
    ClassTeacherCreate,
    ClassTeacherOverview,
    ClassTeacherRead,
    ClassTeacherRelationOverview,
)
from scheme.common import (
    ApiResponse,
    ClassStatus,
    PageData,
    RelationType,
    TeacherStatus,
    TeachingStatus,
)
from scheme.teacher import TeacherRead

router = APIRouter(tags=["班级老师关系"])


def _value(value):
    """兼容 Pydantic 枚举值和普通字符串。"""
    return getattr(value, "value", value)


def to_class_teacher_overview(relation, class_info, teacher) -> ClassTeacherOverview:
    """将三张表转换为详情页使用的嵌套 DTO。"""
    return ClassTeacherOverview(
        id=relation.id,
        class_id=class_info.id,
        class_no=class_info.class_no,
        class_name=class_info.class_name,
        class_status=class_info.class_status,
        teacher_id=teacher.id,
        relation_type=relation.relation_type,
        teacher=TeacherRead.model_validate(teacher),
        created_at=relation.created_at,
        updated_at=relation.updated_at,
    )


def to_relation_overview(relation, class_info, teacher) -> ClassTeacherRelationOverview:
    """将三张表转换为排班管理页使用的扁平 DTO。"""
    return ClassTeacherRelationOverview(
        id=relation.id,
        class_id=class_info.id,
        class_no=class_info.class_no,
        class_name=class_info.class_name,
        class_status=class_info.class_status,
        teacher_id=teacher.id,
        teacher_no=teacher.teacher_no,
        teacher_name=teacher.name,
        specialty=teacher.specialty,
        phone=teacher.phone,
        teacher_status=teacher.teacher_status,
        teaching_status=teacher.teaching_status,
        relation_type=relation.relation_type,
        created_at=relation.created_at,
        updated_at=relation.updated_at,
    )


@router.put(
    "/classes/{class_id}/teachers/{teacher_id}",
    response_model=ApiResponse[ClassTeacherRead],
    status_code=status.HTTP_200_OK,
    responses=ERROR_RESPONSES,
)
def bind_teacher_to_class(
    class_id: int,
    teacher_id: int,
    payload: ClassTeacherCreate,
    db: Session = Depends(get_db),
):
    """幂等绑定老师到班级，并落实未结课班级的三条排班规则。"""
    class_info = class_info_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在")

    teacher = teacher_dao.get_teacher_by_id(db, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="老师不存在")

    relation_type = _value(payload.relation_type)
    if class_info.class_status == "已结课":
        raise HTTPException(status_code=409, detail="已结课班级不能新增老师关系")

    existing = class_teacher_dao.get_active_relation(
        db, class_id, teacher_id, relation_type
    )
    if existing is not None:
        return success(existing)

    if teacher.teacher_status != "在职":
        raise HTTPException(status_code=409, detail="离职老师不能新增班级关系")
    if teacher.teaching_status != "可授课":
        raise HTTPException(status_code=409, detail="暂停授课老师不能新增班级关系")

    other_role = class_teacher_dao.get_active_relation_for_teacher_in_class(
        db, class_id, teacher_id
    )
    if other_role is not None:
        raise HTTPException(
            status_code=409,
            detail="同一班级的班主任和授课老师不能是同一人",
        )

    busy_relation = class_teacher_dao.get_teacher_busy_relation(db, teacher_id)
    if busy_relation is not None:
        raise HTTPException(
            status_code=409,
            detail="老师已在其他未结课班级中任职",
        )

    if relation_type == "班主任":
        head_teacher = class_teacher_dao.get_class_active_head_teacher(db, class_id)
        if head_teacher is not None:
            raise HTTPException(status_code=409, detail="该班级已存在班主任")

    relation = class_teacher_dao.create_relation(
        db, class_id, teacher_id, relation_type
    )
    return success(relation)


@router.get(
    "/classes/{class_id}/teachers",
    response_model=ApiResponse[PageData[ClassTeacherOverview]],
    responses=ERROR_RESPONSES,
)
def list_class_teachers(
    class_id: int,
    relation_type: RelationType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """分页查询指定班级的当前有效老师关系。"""
    class_info = class_info_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在")

    rows, total = class_teacher_dao.list_class_teachers(
        db,
        class_id,
        _value(relation_type),
        page,
        page_size,
    )
    items = [
        to_class_teacher_overview(relation, class_info, teacher)
        for relation, teacher in rows
    ]
    return success(page_data(items, total, page, page_size))


@router.delete(
    "/classes/{class_id}/teachers/{teacher_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=ERROR_RESPONSES,
)
def unbind_teacher_from_class(
    class_id: int,
    teacher_id: int,
    relation_type: RelationType | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """逻辑解除关系；未给 relation_type 时解除该老师在班内全部角色。"""
    if class_info_dao.get_class_by_id(db, class_id) is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if teacher_dao.get_teacher_by_id(db, teacher_id) is None:
        raise HTTPException(status_code=404, detail="老师不存在")

    affected = class_teacher_dao.soft_delete_relations(
        db,
        class_id,
        teacher_id,
        _value(relation_type),
    )
    if affected == 0:
        raise HTTPException(status_code=404, detail="班级老师关系不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/class-teacher-relations",
    response_model=ApiResponse[PageData[ClassTeacherRelationOverview]],
    responses=ERROR_RESPONSES,
)
def list_class_teacher_relations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    class_id: int | None = Query(default=None, ge=1),
    teacher_id: int | None = Query(default=None, ge=1),
    relation_type: RelationType | None = Query(default=None),
    class_keyword: str | None = Query(default=None, max_length=100),
    teacher_keyword: str | None = Query(default=None, max_length=100),
    class_status: ClassStatus | None = Query(default=None),
    teacher_status: TeacherStatus | None = Query(default=None),
    teaching_status: TeachingStatus | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """全局分页查询排班关系，供排班管理页使用。"""
    rows, total = class_teacher_dao.list_relation_overview_rows(
        db=db,
        page=page,
        page_size=page_size,
        class_id=class_id,
        teacher_id=teacher_id,
        relation_type=_value(relation_type),
        class_keyword=class_keyword,
        teacher_keyword=teacher_keyword,
        class_status=_value(class_status),
        teacher_status=_value(teacher_status),
        teaching_status=_value(teaching_status),
    )
    items = [
        to_relation_overview(relation, class_info, teacher)
        for relation, class_info, teacher in rows
    ]
    return success(page_data(items, total, page, page_size))
