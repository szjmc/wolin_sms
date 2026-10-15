"""
老师管理接口
============
POST   /api/v1/teachers                新增老师
GET    /api/v1/teachers                老师分页列表
GET    /api/v1/teachers/{teacher_id}   老师详情
PATCH  /api/v1/teachers/{teacher_id}   更新老师（只传需要修改的字段）
DELETE /api/v1/teachers/{teacher_id}   逻辑删除老师
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, page_data, success
from dao import class_teacher_dao, teacher_dao
from database import get_db
from scheme.common import ApiResponse, PageData, TeacherStatus
from scheme.teacher import TeacherCreate, TeacherRead, TeacherUpdate

router = APIRouter(tags=["老师管理"], responses=ERROR_RESPONSES)


@router.post("/teachers", response_model=ApiResponse[TeacherRead], status_code=201, summary="新增老师")
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db)):
    # 第 1 步：检查老师编号是否已存在（已删除的老师也算）
    if teacher_dao.get_teacher_by_no(db, payload.teacher_no) is not None:
        raise HTTPException(status_code=409, detail="老师编号已存在")

    # 第 2 步：保存到数据库并返回
    teacher = teacher_dao.create_teacher(db, payload.model_dump())
    return success(TeacherRead.model_validate(teacher))


@router.get("/teachers", response_model=ApiResponse[PageData[TeacherRead]], summary="老师分页列表")
def list_teachers(
    teacher_no: str | None = Query(default=None, description="老师编号（精确匹配）"),
    name: str | None = Query(default=None, description="老师姓名（模糊匹配）"),
    specialty: str | None = Query(default=None, description="教学专长（模糊匹配）"),
    teacher_status: TeacherStatus | None = Query(default=None, description="老师状态"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    # 枚举转换成普通字符串
    status_value = None
    if teacher_status is not None:
        status_value = teacher_status.value

    teachers, total = teacher_dao.list_teachers(
        db, page, page_size, teacher_no=teacher_no, name=name, specialty=specialty, teacher_status=status_value
    )

    items = []
    for teacher in teachers:
        items.append(TeacherRead.model_validate(teacher))
    return success(page_data(items, total, page, page_size))


@router.get("/teachers/{teacher_id}", response_model=ApiResponse[TeacherRead], summary="老师详情")
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = teacher_dao.get_teacher_by_id(db, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="老师不存在或已删除")
    return success(TeacherRead.model_validate(teacher))


@router.patch("/teachers/{teacher_id}", response_model=ApiResponse[TeacherRead], summary="更新老师（只传需要修改的字段）")
def update_teacher(teacher_id: int, payload: TeacherUpdate, db: Session = Depends(get_db)):
    teacher = teacher_dao.get_teacher_by_id(db, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="老师不存在或已删除")

    # 只取客户端本次提交的字段
    changes = payload.model_dump(exclude_unset=True)
    teacher = teacher_dao.update_teacher(db, teacher, changes)
    return success(TeacherRead.model_validate(teacher))


@router.delete("/teachers/{teacher_id}", status_code=204, summary="逻辑删除老师")
def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = teacher_dao.get_teacher_by_id(db, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="老师不存在或已删除")

    # 老师还关联着班级，不允许删除
    if class_teacher_dao.count_relations_by_teacher(db, teacher_id) > 0:
        raise HTTPException(status_code=409, detail="该老师还关联着班级，请先解除班级老师关系")

    teacher_dao.delete_teacher(db, teacher)
    return Response(status_code=204)
