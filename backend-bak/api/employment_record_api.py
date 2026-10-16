"""
就业记录接口
============
POST   /api/v1/employment-records                          新增一段就业经历
GET    /api/v1/employment-records                          按条件筛选就业记录
GET    /api/v1/students/{student_id}/employment-records    学生就业历史
GET    /api/v1/classes/{class_id}/employment-records       班级就业记录（按班级快照）
GET    /api/v1/employment-records/{record_id}              就业记录详情
PATCH  /api/v1/employment-records/{record_id}              修改单条就业记录
DELETE /api/v1/employment-records/{record_id}              逻辑删除单条就业记录

规则：
1. 一个学生可以有多条就业记录，新增、修改、删除都只影响当前这一条。
2. 班级相关的查询统一按就业记录里的"班级编号快照 class_no_snapshot"口径，避免学生转班后历史数据变化。
3. 两个快照字段都是必填：新增时服务端必须从学生档案复制填入，不允许为空。
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, get_current_user, calculate_annualized_salary, get_current_user, page_data, success
from api.permissions import check_permission
from dao import class_dao, employment_record_dao, student_dao
from database import get_db
from model.employment_record import EmploymentRecord
from model.user import User
from scheme.common import ApiResponse, PageData, SalaryPeriod
from scheme.employment_record import EmploymentCreate, EmploymentRead, EmploymentUpdate

router = APIRouter(tags=["就业记录"], responses=ERROR_RESPONSES, dependencies=[Depends(get_current_user)])


def to_employment_read(record: EmploymentRecord) -> EmploymentRead:
    """把就业记录 ORM 对象转换成响应模型，并计算年薪等价值"""
    # 年薪等价值不是数据库字段，用 model_copy(update=...) 补上去
    employment_read = EmploymentRead.model_validate(record)
    return employment_read.model_copy(
        update={"annualized_salary": calculate_annualized_salary(record.salary_amount, record.salary_period)}
    )


def get_visible_record(db: Session, record_id: int):
    """
    查询一条"可见"的就业记录：记录本身未删除，并且所属学生也未删除。
    查不到时直接抛出 404 错误。
    """
    record = employment_record_dao.get_record_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="就业记录不存在或已删除")
    if student_dao.get_student_by_id(db, record.student_id) is None:
        raise HTTPException(status_code=404, detail="就业记录所属的学生不存在或已删除")
    return record


@router.post(
    "/employment-records",
    response_model=ApiResponse[EmploymentRead],
    status_code=201,
    summary="新增一段就业经历（不会覆盖该学生已有的就业记录）",
)
def create_employment_record(
    payload: EmploymentCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 第 1 步：学生必须存在且未删除
    student = student_dao.get_student_by_id(db, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    # 第 2 步：权限校验——班主任/授课老师只能给自己班的学生登记就业
    check_permission(current, "employment", student.class_id)

    # 第 3 步：学生必须已经结课才能新增就业信息
    if student.training_graduation_date is None:
        raise HTTPException(status_code=400, detail="该学生尚未结课，不能新增就业信息")
    # 就业开放日期必须大于等于学生的结课日期（时间线不能倒着走）
    if payload.employment_open_date is not None and payload.employment_open_date < student.training_graduation_date:
        raise HTTPException(status_code=400, detail="就业开放日期不能早于学生培训结课日期")

    # 第 4 步：查询学生当前所在的班级，用来生成"班级编号快照"
    # 学生一定有所属班级（建档时必填，删班级前会先检查还有没有学生），
    # 所以正常情况下这里一定能取到；取不到说明数据异常，直接报 404
    class_info = class_dao.get_class_by_id(db, student.class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="学生所属班级不存在或已删除")

    # 第 5 步：组装数据——快照字段由服务端填写，客户端不能传
    data = payload.model_dump()
    data["student_name_snapshot"] = student.name
    data["class_no_snapshot"] = class_info.class_no

    # 第 6 步：新增一条记录（学生信息、快照、就业信息在同一个事务里一起提交）
    record = employment_record_dao.create_record(db, data)
    return success(to_employment_read(record))


@router.get(
    "/employment-records",
    response_model=ApiResponse[PageData[EmploymentRead]],
    summary="按条件筛选就业记录",
)
def list_employment_records(
    student_no: str | None = Query(default=None, description="学生编号（精确匹配）"),
    class_id: int | None = Query(default=None, description="班级ID（按就业记录中的班级编号快照筛选）"),
    company_name: str | None = Query(default=None, description="公司名称（模糊匹配）"),
    employment_city: str | None = Query(default=None, description="就业城市（模糊匹配）"),
    position: str | None = Query(default=None, description="就业岗位（模糊匹配）"),
    salary_period: SalaryPeriod | None = Query(default=None, description="薪资周期：MONTH/YEAR"),
    min_salary: Decimal | None = Query(default=None, ge=0, description="最低原始薪资（建议同时指定 salary_period）"),
    max_salary: Decimal | None = Query(default=None, ge=0, description="最高原始薪资（建议同时指定 salary_period）"),
    min_annualized_salary: Decimal | None = Query(default=None, ge=0, description="最低年薪等价值（跨月薪/年薪比较）"),
    max_annualized_salary: Decimal | None = Query(default=None, ge=0, description="最高年薪等价值（跨月薪/年薪比较）"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    # 班级筛选：先把班级ID换成班级编号，再按就业记录里的"班级编号快照"查询
    class_no = None
    if class_id is not None:
        class_info = class_dao.get_class_by_id(db, class_id)
        if class_info is None:
            # 班级不存在，肯定查不到记录，直接返回空列表
            return success(page_data([], 0, page, page_size))
        class_no = class_info.class_no

    # 薪资周期枚举转换成普通字符串
    period_value = None
    if salary_period is not None:
        period_value = salary_period.value

    records, total = employment_record_dao.list_records(
        db,
        page,
        page_size,
        student_no=student_no,
        class_no_snapshot=class_no,
        company_name=company_name,
        employment_city=employment_city,
        position=position,
        salary_period=period_value,
        min_salary=min_salary,
        max_salary=max_salary,
        min_annualized_salary=min_annualized_salary,
        max_annualized_salary=max_annualized_salary,
    )

    items = []
    for record in records:
        items.append(to_employment_read(record))
    return success(page_data(items, total, page, page_size))


@router.get(
    "/students/{student_id}/employment-records",
    response_model=ApiResponse[PageData[EmploymentRead]],
    summary="学生就业历史（按就业开放日期、Offer 日期、记录ID排序）",
)
def list_student_employment_records(
    student_id: int,
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    if student_dao.get_student_by_id(db, student_id) is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    records, total = employment_record_dao.list_records_by_student(db, student_id, page, page_size)

    items = []
    for record in records:
        items.append(to_employment_read(record))
    return success(page_data(items, total, page, page_size))


@router.get(
    "/classes/{class_id}/employment-records",
    response_model=ApiResponse[PageData[EmploymentRead]],
    summary="班级就业记录（按就业记录中的班级编号快照查询）",
)
def list_class_employment_records(
    class_id: int,
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    class_info = class_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    records, total = employment_record_dao.list_records(
        db, page, page_size, class_no_snapshot=class_info.class_no
    )

    items = []
    for record in records:
        items.append(to_employment_read(record))
    return success(page_data(items, total, page, page_size))


@router.get(
    "/employment-records/{record_id}",
    response_model=ApiResponse[EmploymentRead],
    summary="就业记录详情",
)
def get_employment_record(record_id: int, db: Session = Depends(get_db)):
    record = get_visible_record(db, record_id)
    return success(to_employment_read(record))


@router.patch(
    "/employment-records/{record_id}",
    response_model=ApiResponse[EmploymentRead],
    summary="修改单条就业记录（不影响该学生的其他就业记录）",
)
def update_employment_record(
    record_id: int,
    payload: EmploymentUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_visible_record(db, record_id)
    # 权限：班主任/授课老师只能改自己班学生的就业记录
    check_permission(current, "employment", student_dao.get_student_by_id(db, record.student_id).class_id)

    # 只取客户端本次提交的字段
    changes = payload.model_dump(exclude_unset=True)

    # 用"修改后的值"检查两个日期的关系（包括把开放日期清空这类操作）
    new_open_date = changes.get("employment_open_date", record.employment_open_date)
    new_offer_date = changes.get("offer_date", record.offer_date)
    if new_offer_date is not None and new_open_date is None:
        raise HTTPException(status_code=400, detail="就业尚未开放，填写 Offer 日期之前请先填写就业开放日期")
    if new_open_date is not None and new_offer_date is not None:
        if new_offer_date < new_open_date:
            raise HTTPException(status_code=400, detail="Offer 日期不能早于就业开放日期")

    record = employment_record_dao.update_record(db, record, changes)
    return success(to_employment_read(record))


@router.delete("/employment-records/{record_id}", status_code=204, summary="逻辑删除单条就业记录")
def delete_employment_record(
    record_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_visible_record(db, record_id)
    check_permission(current, "employment", student_dao.get_student_by_id(db, record.student_id).class_id)
    employment_record_dao.delete_record(db, record)
    return Response(status_code=204)


@router.post(
    "/employment-records/{record_id}/accept",
    response_model=ApiResponse[EmploymentRead],
    summary="接受这条 Offer（学生变为已就业，同学生其他 Offer 自动改为已拒绝）",
)
def accept_offer(record_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 第 1 步：记录可见 + 权限校验
    record = get_visible_record(db, record_id)
    student = student_dao.get_student_by_id(db, record.student_id)
    check_permission(current, "employment", student.class_id)

    # 第 2 步：把这条改成"已接受"
    record = employment_record_dao.set_offer_status(db, record, "已接受")

    # 第 3 步：同一学生其他就业记录全部改成"已拒绝"（保留记录本身，不删除）
    employment_record_dao.reject_other_offers(db, record)
    return success(to_employment_read(record))


@router.post(
    "/employment-records/{record_id}/reject",
    response_model=ApiResponse[EmploymentRead],
    summary="拒绝这条 Offer（学生没有其他已接受 Offer 时回到待就业）",
)
def reject_offer(record_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 第 1 步：记录可见 + 权限校验
    record = get_visible_record(db, record_id)
    student = student_dao.get_student_by_id(db, record.student_id)
    check_permission(current, "employment", student.class_id)

    # 第 2 步：把这条改成"已拒绝"；其他记录不动，学生状态由接口层根据是否有"已接受"动态判断
    record = employment_record_dao.set_offer_status(db, record, "已拒绝")
    return success(to_employment_read(record))
