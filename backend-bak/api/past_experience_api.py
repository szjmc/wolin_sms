"""学生过往经历接口。"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, page_data, success
from dao import past_experience_dao, students_dao
from database import get_db
from scheme.common import ApiResponse, PageData
from scheme.past_experience import (
    PastExperienceCreate,
    PastExperienceRead,
    PastExperienceUpdate,
)

router = APIRouter(tags=["学生过往经历"], responses=ERROR_RESPONSES)


def get_visible_experience(db: Session, experience_id: int):
    """经历本身及所属学生都未删除时才允许普通业务访问。"""
    experience = past_experience_dao.get_experience_by_id(db, experience_id)
    if experience is None:
        raise HTTPException(status_code=404, detail="过往经历不存在或已删除")
    if students_dao.get_student_by_id(db, experience.student_id) is None:
        raise HTTPException(
            status_code=404,
            detail="过往经历所属的学生不存在或已删除",
        )
    return experience


@router.post(
    "/students/{student_id}/past-experiences",
    response_model=ApiResponse[PastExperienceRead],
    status_code=201,
    summary="为学生新增一条过往经历",
)
def create_past_experience(
    payload: PastExperienceCreate,
    student_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    if students_dao.get_student_by_id(db, student_id) is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    data = payload.model_dump()
    data["student_id"] = student_id
    experience = past_experience_dao.create_experience(db, data)
    return success(PastExperienceRead.model_validate(experience))


@router.get(
    "/students/{student_id}/past-experiences",
    response_model=ApiResponse[PageData[PastExperienceRead]],
    summary="查询学生的过往经历列表",
)
def list_past_experiences(
    student_id: int = Path(gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if students_dao.get_student_by_id(db, student_id) is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    experiences, total = past_experience_dao.list_experiences_by_student(
        db, student_id, page, page_size
    )
    items = [
        PastExperienceRead.model_validate(experience)
        for experience in experiences
    ]
    return success(page_data(items, total, page, page_size))


@router.get(
    "/past-experiences/{experience_id}",
    response_model=ApiResponse[PastExperienceRead],
    summary="过往经历详情",
)
def get_past_experience(
    experience_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    experience = get_visible_experience(db, experience_id)
    return success(PastExperienceRead.model_validate(experience))


@router.patch(
    "/past-experiences/{experience_id}",
    response_model=ApiResponse[PastExperienceRead],
    summary="修改过往经历",
)
def update_past_experience(
    payload: PastExperienceUpdate,
    experience_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    experience = get_visible_experience(db, experience_id)
    changes = payload.model_dump(exclude_unset=True)

    new_amount = changes.get(
        "past_salary_amount", experience.past_salary_amount
    )
    new_period = changes.get(
        "past_salary_period", experience.past_salary_period
    )
    if new_amount is not None and new_period is None:
        raise HTTPException(
            status_code=400,
            detail="填写过往薪资金额时必须同时填写薪资周期",
        )

    experience = past_experience_dao.update_experience(
        db, experience, changes
    )
    return success(PastExperienceRead.model_validate(experience))


@router.delete(
    "/past-experiences/{experience_id}",
    status_code=204,
    summary="逻辑删除过往经历",
)
def delete_past_experience(
    experience_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    experience = get_visible_experience(db, experience_id)
    past_experience_dao.delete_experience(db, experience)
    return Response(status_code=204)
