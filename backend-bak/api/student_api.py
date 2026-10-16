"""
学生信息管理接口
================
POST   /api/v1/students                新增学生
GET    /api/v1/students                学生分页列表
GET    /api/v1/students/{student_id}   学生详情（含动态计算的年龄）
PATCH  /api/v1/students/{student_id}   更新学生（只传需要修改的字段）
DELETE /api/v1/students/{student_id}   逻辑删除学生
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, get_current_user, calculate_birth_date_cutoff, get_current_user, page_data, success, to_student_read
from api.permissions import check_permission
from dao import class_dao, employment_record_dao, student_dao
from database import get_db
from scheme.common import ApiResponse, Gender, PageData
from model.user import User
from scheme.student import StudentCreate, StudentRead, StudentUpdate

router = APIRouter(tags=["学生管理"], responses=ERROR_RESPONSES, dependencies=[Depends(get_current_user)])


def build_reads(db: Session, students: list):
    """
    把一批学生对象转成响应模型，并补上就业状态。
    就业状态规则：有一条"已接受"的 Offer 就是已就业，否则是待就业。
    """
    accepted_ids = employment_record_dao.list_accepted_student_ids(db)
    items = []
    for student in students:
        read = to_student_read(student)
        if student.id in accepted_ids:
            read.employment_status = "已就业"
        items.append(read)
    return items


@router.post("/students", response_model=ApiResponse[StudentRead], status_code=201, summary="新增学生")
def create_student(
    payload: StudentCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 第 1 步：所属班级必须存在且未删除
    if class_dao.get_class_by_id(db, payload.class_id) is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    # 第 1.5 步：权限校验——班主任/授课老师只能给自己班加学生
    check_permission(current, "student", payload.class_id)

    # 第 2 步：检查学生编号是否重复（已删除的学生也算，因为编号全表唯一）
    if student_dao.get_student_by_no(db, payload.student_no) is not None:
        raise HTTPException(status_code=409, detail="学生编号已存在")

    # 第 3 步：保存到数据库
    student = student_dao.create_student(db, payload.model_dump())

    # 第 4 步：组装响应（年龄由出生日期动态计算，就业状态按已接受 Offer 判断）
    return success(build_reads(db, [student])[0])


@router.get("/students", response_model=ApiResponse[PageData[StudentRead]], summary="学生分页列表")
def list_students(
    student_no: str | None = Query(default=None, description="学生编号（精确匹配）"),
    name: str | None = Query(default=None, description="学生姓名（模糊匹配）"),
    class_id: int | None = Query(default=None, description="班级ID"),
    gender: Gender | None = Query(default=None, description="性别"),
    age_gt: int | None = Query(default=None, ge=0, le=150, description="年龄大于该值（按出生日期动态计算）"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    # 性别枚举转换成普通字符串
    gender_value = None
    if gender is not None:
        gender_value = gender.value

    # 年龄条件换算成出生日期条件：年龄 > age_gt 等价于 出生日期 <= 截止日期
    max_birth_date = None
    if age_gt is not None:
        max_birth_date = calculate_birth_date_cutoff(age_gt)

    students, total = student_dao.list_students(
        db,
        page,
        page_size,
        student_no=student_no,
        name=name,
        class_id=class_id,
        gender=gender_value,
        max_birth_date=max_birth_date,
    )

    items = build_reads(db, students)
    return success(page_data(items, total, page, page_size))


@router.get("/students/{student_id}", response_model=ApiResponse[StudentRead], summary="学生详情")
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = student_dao.get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")
    return success(build_reads(db, [student])[0])


@router.patch("/students/{student_id}", response_model=ApiResponse[StudentRead], summary="更新学生（只传需要修改的字段）")
def update_student(
    student_id: int,
    payload: StudentUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 第 1 步：学生必须存在且未删除
    student = student_dao.get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    # 第 1.5 步：权限校验——班主任/授课老师只能改自己班的学生（转班还要对目标班有权限）
    check_permission(current, "student", student.class_id)

    # 第 2 步：只取客户端本次真正提交的字段（不要用 exclude_none，显式传 null 表示清空可空字段）
    changes = payload.model_dump(exclude_unset=True)

    # 第 3 步：如果修改了班级，新班级必须存在且未删除
    if "class_id" in changes:
        if class_dao.get_class_by_id(db, changes["class_id"]) is None:
            raise HTTPException(status_code=404, detail="班级不存在或已删除")
        # 转班属于跨班级操作，目标班也必须在权限范围内
        check_permission(current, "student", changes["class_id"])

    # 第 4 步：用"修改后的值"检查培训日期先后顺序（只修改其中一个日期时也要检查）
    new_enrollment_date = changes.get("training_enrollment_date", student.training_enrollment_date)
    new_graduation_date = changes.get("training_graduation_date", student.training_graduation_date)
    if new_enrollment_date is not None and new_graduation_date is not None:
        if new_graduation_date < new_enrollment_date:
            raise HTTPException(status_code=400, detail="培训结课日期不能早于培训入学日期")

    # 第 5 步：保存修改
    student = student_dao.update_student(db, student, changes)
    return success(build_reads(db, [student])[0])


@router.delete("/students/{student_id}", status_code=204, summary="逻辑删除学生")
def delete_student(
    student_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = student_dao.get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    # 权限校验：只能删除自己班的学生
    check_permission(current, "student", student.class_id)

    # 只给学生打删除标记；成绩、过往经历、就业记录全部保留（普通查询会自动隐藏）
    student_dao.delete_student(db, student)
    return Response(status_code=204)
