# 班级路由层
# 作用：接收前端请求，调用 dao，返回 json
# 班级路由层
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from scheme.class_info import ClassCreate, ClassUpdate
from dao import class_info_dao

router = APIRouter(prefix="/classes", tags=["班级管理"])


@router.post("", summary="新增班级")
# 新增班级接口，接收校验后的入参，调用DAO层完成持久化。
def create_class(payload: ClassCreate, db: Session = Depends(get_db)):
    try:
        data = class_info_dao.create_class(db, payload)
        return {"code": 200, "message": "新增成功", "data": data}
    except class_info_dao.BusinessError as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@router.get("", summary="查询班级列表")
def list_classes(
    class_name: str | None = Query(None, description="按班级名称模糊查询"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db)
):
    total, items = class_info_dao.list_classes(db, class_name, page, page_size)
    return {
        "code": 200, "total": total, "page": page, "page_size": page_size,
        "data": [class_info_dao.class_to_dict(c) for c in items]
    }


@router.get("/{class_no}", summary="查询班级详情（老师）")
def get_class(class_no: str, db: Session = Depends(get_db)):
    data = class_info_dao.get_class_with_teachers(db, class_no)
    if not data:
        raise HTTPException(status_code=404, detail="班级不存在")
    return {"code": 200, "data": data}


@router.put("/{class_no}", summary="更新班级信息")
def update_class(class_no: str, payload: ClassUpdate, db: Session = Depends(get_db)):
    try:
        data = class_info_dao.update_class(db, class_no, payload)
        return {"code": 200, "message": "更新成功", "data": data}
    except class_info_dao.BusinessError as e:
        raise HTTPException(status_code=e.code, detail=e.message)


@router.delete("/{class_no}", summary="删除班级")
def delete_class(class_no: str, db: Session = Depends(get_db)):
    try:
        class_info_dao.delete_class(db, class_no)
        return {"code": 200, "message": "删除成功"}
    except class_info_dao.BusinessError as e:
        raise HTTPException(status_code=e.code, detail=e.message)


#预留接口
@router.get("/{class_no}/statistics", summary="查询班级统计（及格率）")
def get_class_statistics(class_no: str, db: Session = Depends(get_db)):
    data = class_info_dao.get_class_statistics(db, class_no)
    if not data:
        raise HTTPException(status_code=404, detail="班级不存在")
    return {"code": 200, "data": data}