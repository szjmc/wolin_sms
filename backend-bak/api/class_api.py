"""
班级管理接口
============
POST   /api/v1/classes              新增班级
GET    /api/v1/classes              班级分页列表
GET    /api/v1/classes/{class_id}   班级详情
PATCH  /api/v1/classes/{class_id}   更新班级（只传需要修改的字段）
DELETE /api/v1/classes/{class_id}   逻辑删除班级（班级下有学生时禁止删除，防止孤儿数据）
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, get_current_user, get_current_user, page_data, success
from api.permissions import check_permission
from dao import class_dao, class_teacher_dao, student_dao
from database import get_db
from scheme.class_info import ClassCreate, ClassRead, ClassUpdate
from scheme.common import ApiResponse, ClassStatus, PageData
from model.user import User

router = APIRouter(tags=["班级管理"], responses=ERROR_RESPONSES, dependencies=[Depends(get_current_user)])


@router.post("/classes", response_model=ApiResponse[ClassRead], status_code=201, summary="新增班级")
def create_class(
    payload: ClassCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 第 0 步：只有管理员能建班级（组织配置类操作）
    check_permission(current, "setup")
    # 第 1 步：检查班级编号是否已存在（已删除的班级也算，因为编号全表唯一）
    if class_dao.get_class_by_no(db, payload.class_no) is not None:
        raise HTTPException(status_code=409, detail="班级编号已存在")

    # 第 2 步：保存到数据库
    class_info = class_dao.create_class(db, payload.model_dump())

    # 第 3 步：把 ORM 对象转换成响应模型返回
    return success(ClassRead.model_validate(class_info))


@router.get("/classes", response_model=ApiResponse[PageData[ClassRead]], summary="班级分页列表")
def list_classes(
    class_no: str | None = Query(default=None, description="班级编号（精确匹配）"),
    class_name: str | None = Query(default=None, description="班级名称（模糊匹配）"),
    class_status: ClassStatus | None = Query(default=None, description="班级状态"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    # 枚举转换成普通字符串，再交给数据库查询
    status_value = None
    if class_status is not None:
        status_value = class_status.value

    class_list, total = class_dao.list_classes(
        db, page, page_size, class_no=class_no, class_name=class_name, class_status=status_value
    )

    items = []
    for class_info in class_list:
        items.append(ClassRead.model_validate(class_info))
    return success(page_data(items, total, page, page_size))


@router.get("/classes/{class_id}", response_model=ApiResponse[ClassRead], summary="班级详情")
def get_class(class_id: int, db: Session = Depends(get_db)):
    class_info = class_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")
    return success(ClassRead.model_validate(class_info))


@router.patch("/classes/{class_id}", response_model=ApiResponse[ClassRead], summary="更新班级（只传需要修改的字段）")
def update_class(
    class_id: int,
    payload: ClassUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 第 1 步：班级必须存在且未删除
    class_info = class_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    # 第 1.5 步：权限校验——班主任只能改自己带的班
    check_permission(current, "class", class_id)

    # 第 2 步：只取客户端本次真正提交的字段（没提交的字段保持原值，不会被改成 null）
    changes = payload.model_dump(exclude_unset=True)

    # 第 3 步：用"修改后的值"检查开班日期和结课日期的先后顺序
    new_start_date = changes.get("start_date", class_info.start_date)
    new_completion_date = changes.get("completion_date", class_info.completion_date)
    if new_completion_date is not None and new_completion_date < new_start_date:
        raise HTTPException(status_code=400, detail="班级结课日期不能早于开班日期")

    # 第 4 步：保存修改
    class_info = class_dao.update_class(db, class_info, changes)
    return success(ClassRead.model_validate(class_info))


@router.delete("/classes/{class_id}", status_code=204, summary="逻辑删除班级")
def delete_class(
    class_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 第 1 步：班级必须存在且未删除
    class_info = class_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    # 第 1.5 步：权限校验——班主任只能删自己带的班
    check_permission(current, "class", class_id)

    # 第 2 步：班级下还有未删除的学生，直接拒绝，防止产生找不到班级的孤儿学生
    if student_dao.count_students_by_class(db, class_id) > 0:
        raise HTTPException(status_code=409, detail="该班级下仍有学生，不能删除")

    # 第 3 步：班级还关联着老师，不允许删除
    if class_teacher_dao.count_relations_by_class(db, class_id) > 0:
        raise HTTPException(status_code=409, detail="该班级还关联着老师，请先解除班级老师关系")

    # 第 4 步：逻辑删除，删除成功返回 204（没有响应体）
    class_dao.delete_class(db, class_info)
    return Response(status_code=204)
