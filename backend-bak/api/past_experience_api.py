"""
学生过往经历接口
================
POST   /api/v1/students/{student_id}/past-experiences   为学生新增一条过往经历
GET    /api/v1/students/{student_id}/past-experiences   查询学生的过往经历列表
GET    /api/v1/past-experiences/{experience_id}         过往经历详情
PATCH  /api/v1/past-experiences/{experience_id}         修改过往经历
DELETE /api/v1/past-experiences/{experience_id}         逻辑删除过往经历
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, get_current_user, page_data, success
from dao import past_experience_dao, student_dao
from database import get_db
from scheme.common import ApiResponse, PageData
from scheme.past_experience import PastExperienceCreate, PastExperienceRead, PastExperienceUpdate

router = APIRouter(tags=["学生过往经历"], responses=ERROR_RESPONSES, dependencies=[Depends(get_current_user)])


def get_visible_experience(db: Session, experience_id: int):
    """
    查询一条"可见"的过往经历：经历本身未删除，并且所属学生也未删除。
    查不到时直接抛出 404 错误。
    """
    experience = past_experience_dao.get_experience_by_id(db, experience_id)
    if experience is None:
        raise HTTPException(status_code=404, detail="过往经历不存在或已删除")
    if student_dao.get_student_by_id(db, experience.student_id) is None:
        raise HTTPException(status_code=404, detail="过往经历所属的学生不存在或已删除")
    return experience


@router.post(
    "/students/{student_id}/past-experiences",
    response_model=ApiResponse[PastExperienceRead],
    status_code=201,
    summary="为学生新增一条过往经历",
)
def create_past_experience(student_id: int, payload: PastExperienceCreate, db: Session = Depends(get_db)):
    # 第 1 步：学生必须存在且未删除
    if student_dao.get_student_by_id(db, student_id) is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    # 第 2 步：组装数据，学生ID来自 URL 路径
    data = payload.model_dump()
    data["student_id"] = student_id

    # 第 3 步：保存（一个学生可以有多条经历，新增不影响已有经历）
    experience = past_experience_dao.create_experience(db, data)
    return success(PastExperienceRead.model_validate(experience))


@router.get(
    "/students/{student_id}/past-experiences",
    response_model=ApiResponse[PageData[PastExperienceRead]],
    summary="查询学生的过往经历列表",
)
def list_past_experiences(
    student_id: int,
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    if student_dao.get_student_by_id(db, student_id) is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    experiences, total = past_experience_dao.list_experiences_by_student(db, student_id, page, page_size)

    items = []
    for experience in experiences:
        items.append(PastExperienceRead.model_validate(experience))
    return success(page_data(items, total, page, page_size))


@router.get(
    "/past-experiences/{experience_id}",
    response_model=ApiResponse[PastExperienceRead],
    summary="过往经历详情",
)
def get_past_experience(experience_id: int, db: Session = Depends(get_db)):
    experience = get_visible_experience(db, experience_id)
    return success(PastExperienceRead.model_validate(experience))


@router.patch(
    "/past-experiences/{experience_id}",
    response_model=ApiResponse[PastExperienceRead],
    summary="修改过往经历（只传需要修改的字段）",
)
def update_past_experience(experience_id: int, payload: PastExperienceUpdate, db: Session = Depends(get_db)):
    experience = get_visible_experience(db, experience_id)

    # 只取客户端本次提交的字段
    changes = payload.model_dump(exclude_unset=True)

    # 用"修改后的值"检查：有薪资金额时必须有薪资周期
    new_amount = changes.get("past_salary_amount", experience.past_salary_amount)
    new_period = changes.get("past_salary_period", experience.past_salary_period)
    if new_amount is not None and new_period is None:
        raise HTTPException(status_code=400, detail="填写过往薪资金额时必须同时填写薪资周期")

    experience = past_experience_dao.update_experience(db, experience, changes)
    return success(PastExperienceRead.model_validate(experience))


@router.delete("/past-experiences/{experience_id}", status_code=204, summary="逻辑删除过往经历")
def delete_past_experience(experience_id: int, db: Session = Depends(get_db)):
    experience = get_visible_experience(db, experience_id)
    past_experience_dao.delete_experience(db, experience)
    return Response(status_code=204)
