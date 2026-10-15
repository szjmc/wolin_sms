"""学生管理接口。

POST/GET/PATCH/DELETE 均按数字 student_id 操作并使用统一响应格式。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import (
    ERROR_RESPONSES,
    calculate_birth_date_cutoff,
    page_data,
    success,
    to_student_read,
)
from dao import class_info_dao, students_dao
from database import get_db
from scheme.common import ApiResponse, Gender, PageData
from scheme.students import StudentCreate, StudentRead, StudentUpdate


# [修改说明] 原代码：路由使用 /student、/student/list 并按 student_no 查改删，返回裸模型或 records；修改原因：与前端数字 ID、复数资源路径和全局 ApiResponse/PageData 契约不一致；修改为：保留 api/students_api.py 与小组 DAO，五个核心接口统一为 /students 及 /students/{student_id}。
router = APIRouter(tags=["学生管理"], responses=ERROR_RESPONSES)


def _to_student_read(db: Session, student) -> StudentRead:
    """补入所属班级展示信息及动态年龄。"""
    class_info = class_info_dao.get_class_by_id(db, student.class_id)
    return to_student_read(student, class_info)


@router.post(
    "/students",
    response_model=ApiResponse[StudentRead],
    status_code=201,
    summary="新增学生",
)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    if class_info_dao.get_class_by_id(db, payload.class_id) is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    # 已逻辑删除记录也占用学生编号，避免历史档案身份混淆。
    if students_dao.get_student_by_no(db, payload.student_no) is not None:
        raise HTTPException(status_code=409, detail="学生编号已存在")

    student = students_dao.create_student(db, payload.model_dump())
    return success(_to_student_read(db, student))


@router.get(
    "/students",
    response_model=ApiResponse[PageData[StudentRead]],
    summary="学生分页列表",
)
def list_students(
    q: str | None = Query(
        default=None, max_length=100, description="姓名或学号组合模糊搜索"
    ),
    student_no: str | None = Query(
        default=None, max_length=30, description="学生编号（精确匹配）"
    ),
    name: str | None = Query(
        default=None, max_length=50, description="学生姓名（模糊匹配）"
    ),
    class_id: int | None = Query(default=None, ge=1, description="班级 ID"),
    gender: Gender | None = Query(default=None, description="性别"),
    age_gt: int | None = Query(
        default=None, ge=0, le=150, description="年龄大于该值"
    ),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="每页条数，最大 100"
    ),
    db: Session = Depends(get_db),
):
    gender_value = gender.value if gender is not None else None
    max_birth_date = (
        calculate_birth_date_cutoff(age_gt) if age_gt is not None else None
    )

    students, total = students_dao.list_students(
        db,
        page,
        page_size,
        q=q,
        student_no=student_no,
        name=name,
        class_id=class_id,
        gender=gender_value,
        max_birth_date=max_birth_date,
    )
    items = [_to_student_read(db, student) for student in students]
    return success(page_data(items, total, page, page_size))


@router.get(
    "/students/{student_id}",
    response_model=ApiResponse[StudentRead],
    summary="学生详情",
)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = students_dao.get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")
    return success(_to_student_read(db, student))


@router.patch(
    "/students/{student_id}",
    response_model=ApiResponse[StudentRead],
    summary="更新学生（只传需要修改的字段）",
)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
):
    student = students_dao.get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    changes = payload.model_dump(exclude_unset=True)
    if "class_id" in changes:
        if class_info_dao.get_class_by_id(db, changes["class_id"]) is None:
            raise HTTPException(status_code=404, detail="班级不存在或已删除")

    # 结合数据库原值检查只更新一个培训日期时的先后关系。
    new_enrollment_date = changes.get(
        "training_enrollment_date", student.training_enrollment_date
    )
    new_graduation_date = changes.get(
        "training_graduation_date", student.training_graduation_date
    )
    if (
        new_enrollment_date is not None
        and new_graduation_date is not None
        and new_graduation_date < new_enrollment_date
    ):
        raise HTTPException(
            status_code=400, detail="培训结课日期不能早于培训入学日期"
        )

    student = students_dao.update_student(db, student, changes)
    return success(_to_student_read(db, student))


@router.delete(
    "/students/{student_id}",
    status_code=204,
    summary="逻辑删除学生",
)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = students_dao.get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    students_dao.delete_student(db, student)
    return Response(status_code=204)
