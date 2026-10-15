"""就业记录管理接口。

在小组原 ``stu_records_api.py`` 路由框架上补齐多段就业历史、创建快照、组合筛选、
逻辑删除，以及前端使用的筛选项和薪资对比接口。
"""
import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from api.common import (
    ERROR_RESPONSES,
    calculate_age,
    calculate_annualized_salary,
    page_data,
    round_2,
    success,
)
from dao import class_info_dao, past_experience_dao, stu_records_dao, students_dao
from database import get_db
from scheme.common import ApiResponse, PageData, SalaryPeriod
from scheme.stu_records_scheme import (
    EmploymentOptions,
    EmploymentRecordCreate,
    EmploymentRecordOut,
    EmploymentRecordUpdate,
    SalaryComparisonOut,
)


# [修改说明] 原代码：导入不存在的 class_dao/student_dao，且只验证“Offer 早于开放日”；修改原因：模块无法加载，有 Offer 但没有开放日期也能落库；修改为：复用现有 class_info_dao/students_dao，并在创建和 PATCH 合并数据库原值后同时校验两条日期规则。
router = APIRouter(tags=["就业记录管理"], responses=ERROR_RESPONSES)

_SNAPSHOT_FIELDS = {
    "past_salary_amount",
    "past_salary_period",
    "previous_position",
    "past_graduation_date",
}
_OPTIONAL_TEXT_FIELDS = {"employment_city", "position", "previous_position"}


def _record_or_404(db: Session, record_id: int):
    record = stu_records_dao.get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="就业记录不存在或所属学生已删除")
    return record


def _record_out(db: Session, record) -> EmploymentRecordOut:
    """组装当前关联信息与不落库的年化薪资、毕业年限。"""
    student = students_dao.get_student_by_id(db, record.student_id)
    class_info = class_info_dao.get_class(db, record.class_no_snapshot)
    data = {
        "id": record.id,
        "student_id": record.student_id,
        "student_no": getattr(student, "student_no", None),
        "student_name_snapshot": record.student_name_snapshot,
        "class_id": getattr(class_info, "id", None),
        "class_no_snapshot": record.class_no_snapshot,
        "employment_open_date": record.employment_open_date,
        "offer_date": record.offer_date,
        "company_name": record.company_name,
        "employment_city": record.employment_city,
        "position": record.position,
        "salary_amount": record.salary_amount,
        "salary_period": record.salary_period,
        "annualized_salary": calculate_annualized_salary(
            record.salary_amount, record.salary_period
        ),
        "past_salary_amount": record.past_salary_amount,
        "past_salary_period": record.past_salary_period,
        "previous_position": record.previous_position,
        "past_graduation_date": record.past_graduation_date,
        "graduation_years": calculate_age(record.past_graduation_date),
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    return EmploymentRecordOut.model_validate(data)


def _validate_dates(open_date, offer_date, status_code: int):
    if offer_date is not None and open_date is None:
        raise HTTPException(
            status_code=status_code,
            detail="就业尚未开放，填写 Offer 日期之前请先填写就业开放日期",
        )
    if open_date is not None and offer_date is not None and offer_date < open_date:
        raise HTTPException(
            status_code=status_code,
            detail="Offer 日期不能早于就业开放日期",
        )


def _validate_past_snapshot(amount, period, graduation_date, status_code: int):
    if amount is not None and period is None:
        raise HTTPException(
            status_code=status_code,
            detail="填写以往薪资金额时必须同时填写薪资周期",
        )
    if graduation_date is not None and graduation_date > date.today():
        raise HTTPException(
            status_code=status_code,
            detail="学历毕业日期不能晚于今天",
        )


def _years_ago(years: int) -> date:
    """返回今天往前 years 个完整周年的日期，兼容 2 月 29 日。"""
    today = date.today()
    target_year = today.year - years
    day = today.day
    if today.month == 2 and today.day == 29 and not calendar.isleap(target_year):
        day = 28
    return date(target_year, today.month, day)


def _normalize_optional_text(changes: dict):
    """可选文本的空字符串按未填写保存为 null。"""
    for field_name in _OPTIONAL_TEXT_FIELDS:
        if changes.get(field_name) == "":
            changes[field_name] = None


def _comparison(record) -> SalaryComparisonOut:
    after = calculate_annualized_salary(record.salary_amount, record.salary_period)
    before = None
    if record.past_salary_amount is not None and record.past_salary_period is not None:
        before = calculate_annualized_salary(
            record.past_salary_amount, record.past_salary_period
        )

    increase = round_2(after - before) if before is not None else None
    percent = None
    if before not in (None, Decimal("0")):
        percent = ((after - before) * Decimal("100") / before).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    return SalaryComparisonOut.model_validate(
        {
            "employment_record_id": record.id,
            "student_id": record.student_id,
            "student_name_snapshot": record.student_name_snapshot,
            "previous_position": record.previous_position,
            "position": record.position,
            "past_salary_amount": record.past_salary_amount,
            "past_salary_period": record.past_salary_period,
            "salary_amount": record.salary_amount,
            "salary_period": record.salary_period,
            "past_annualized_salary": before,
            "annualized_salary": after,
            "monthly_before": round_2(before / 12) if before is not None else None,
            "monthly_after": round_2(after / 12),
            "annual_increase": increase,
            "increase_percent": percent,
            "comparison_available": before is not None,
        }
    )


# [修改说明] 原代码：没有筛选项、就业前快照和薪资对比能力；修改原因：就业列表及详情页会请求这些数据，且直接读取当前学生经历会破坏历史；修改为：新增 options/comparison，只基于可见就业记录及其创建快照计算，不反查当前过往经历。
@router.get(
    "/employment-records/options",
    response_model=ApiResponse[EmploymentOptions],
    summary="就业筛选项",
)
def employment_filter_options(db: Session = Depends(get_db)):
    cities, positions = stu_records_dao.list_filter_options(db)
    return success(EmploymentOptions(cities=cities, positions=positions))


@router.post(
    "/employment-records",
    response_model=ApiResponse[EmploymentRecordOut],
    status_code=201,
    summary="新增就业记录",
)
def create_employment_record(
    payload: EmploymentRecordCreate,
    db: Session = Depends(get_db),
):
    student = students_dao.get_student_by_id(db, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    class_info = class_info_dao.get_class_by_id(db, student.class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="学生所属班级不存在或已删除")

    latest = past_experience_dao.get_latest_experience_by_student(db, student.id)
    submitted = payload.model_fields_set
    data = payload.model_dump(exclude=_SNAPSHOT_FIELDS)

    # 各快照字段只有“未提交”时才回退到最近经历；显式 null 会原样保存。
    for field_name, source_name in (
        ("past_salary_amount", "past_salary_amount"),
        ("past_salary_period", "past_salary_period"),
        ("previous_position", "previous_position"),
        ("past_graduation_date", "graduation_date"),
    ):
        if field_name in submitted:
            data[field_name] = getattr(payload, field_name)
        else:
            data[field_name] = getattr(latest, source_name, None)

    _normalize_optional_text(data)
    _validate_dates(data["employment_open_date"], data["offer_date"], 422)
    _validate_past_snapshot(
        data["past_salary_amount"],
        data["past_salary_period"],
        data["past_graduation_date"],
        422,
    )

    data["student_name_snapshot"] = student.name
    data["class_no_snapshot"] = class_info.class_no
    record = stu_records_dao.create_record(db, data)
    return success(_record_out(db, record))


@router.get(
    "/employment-records",
    response_model=ApiResponse[PageData[EmploymentRecordOut]],
    summary="就业记录分页列表",
)
def list_employment_records(
    q: str | None = Query(default=None, max_length=150, description="学生、学号或公司"),
    student_no: str | None = Query(default=None, max_length=30),
    class_id: int | None = Query(default=None, ge=1),
    company_name: str | None = Query(default=None, max_length=150),
    employment_city: str | None = Query(default=None, max_length=100),
    position: str | None = Query(default=None, max_length=100),
    salary_period: SalaryPeriod | None = Query(default=None),
    salary_basis: SalaryPeriod | None = Query(
        default=None, description="min/max_salary 使用的统一口径"
    ),
    min_salary: Decimal | None = Query(default=None, ge=0),
    max_salary: Decimal | None = Query(default=None, ge=0),
    min_annualized_salary: Decimal | None = Query(default=None, ge=0),
    max_annualized_salary: Decimal | None = Query(default=None, ge=0),
    min_graduation_years: int | None = Query(default=None, ge=0, le=100),
    max_graduation_years: int | None = Query(default=None, ge=0, le=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if min_salary is not None and max_salary is not None and min_salary > max_salary:
        raise HTTPException(status_code=422, detail="最低薪资不能大于最高薪资")
    if (
        min_annualized_salary is not None
        and max_annualized_salary is not None
        and min_annualized_salary > max_annualized_salary
    ):
        raise HTTPException(status_code=422, detail="最低年化薪资不能大于最高年化薪资")
    if (
        min_graduation_years is not None
        and max_graduation_years is not None
        and min_graduation_years > max_graduation_years
    ):
        raise HTTPException(status_code=422, detail="毕业年限区间不合法")

    class_no = None
    if class_id is not None:
        class_info = class_info_dao.get_class_by_id(db, class_id)
        if class_info is None:
            return success(page_data([], 0, page, page_size))
        class_no = class_info.class_no

    records, total = stu_records_dao.list_records(
        db,
        page,
        page_size,
        q=q,
        student_no=student_no,
        class_no=class_no,
        company_name=company_name,
        employment_city=employment_city,
        position=position,
        salary_period=salary_period.value if salary_period is not None else None,
        salary_basis=salary_basis.value if salary_basis is not None else None,
        min_salary=min_salary,
        max_salary=max_salary,
        min_annualized_salary=min_annualized_salary,
        max_annualized_salary=max_annualized_salary,
        graduation_before_or_on=(
            _years_ago(min_graduation_years)
            if min_graduation_years is not None
            else None
        ),
        graduation_after=(
            _years_ago(max_graduation_years + 1)
            if max_graduation_years is not None
            else None
        ),
    )
    items = [_record_out(db, record) for record in records]
    return success(page_data(items, total, page, page_size))


@router.get(
    "/students/{student_id}/employment-records",
    response_model=ApiResponse[PageData[EmploymentRecordOut]],
    summary="学生就业历史",
)
def list_student_employment_records(
    student_id: int = Path(gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if students_dao.get_student_by_id(db, student_id) is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")
    records, total = stu_records_dao.list_records_by_student(
        db, student_id, page, page_size
    )
    return success(
        page_data(
            [_record_out(db, record) for record in records],
            total,
            page,
            page_size,
        )
    )


@router.get(
    "/classes/{class_id}/employment-records",
    response_model=ApiResponse[PageData[EmploymentRecordOut]],
    summary="班级历史就业记录",
)
def list_class_employment_records(
    class_id: int = Path(gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    class_info = class_info_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")
    records, total = stu_records_dao.list_records_by_class_no(
        db, class_info.class_no, page, page_size
    )
    return success(
        page_data(
            [_record_out(db, record) for record in records],
            total,
            page,
            page_size,
        )
    )


@router.get(
    "/employment-records/{record_id}/comparison",
    response_model=ApiResponse[SalaryComparisonOut],
    summary="本条就业记录的岗位与薪资对比",
)
def compare_employment_salary(
    record_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    return success(_comparison(_record_or_404(db, record_id)))


@router.get(
    "/employment-records/{record_id}",
    response_model=ApiResponse[EmploymentRecordOut],
    summary="就业记录详情",
)
def get_employment_record(
    record_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    return success(_record_out(db, _record_or_404(db, record_id)))


@router.patch(
    "/employment-records/{record_id}",
    response_model=ApiResponse[EmploymentRecordOut],
    summary="局部更新一条就业记录",
)
def update_employment_record(
    payload: EmploymentRecordUpdate,
    record_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    record = _record_or_404(db, record_id)
    changes = payload.model_dump(exclude_unset=True)
    _normalize_optional_text(changes)

    open_date = changes.get("employment_open_date", record.employment_open_date)
    offer_date = changes.get("offer_date", record.offer_date)
    _validate_dates(open_date, offer_date, 400)

    past_amount = changes.get("past_salary_amount", record.past_salary_amount)
    past_period = changes.get("past_salary_period", record.past_salary_period)
    graduation_date = changes.get(
        "past_graduation_date", record.past_graduation_date
    )
    _validate_past_snapshot(past_amount, past_period, graduation_date, 400)

    record = stu_records_dao.update_record(db, record, changes)
    return success(_record_out(db, record))


@router.delete(
    "/employment-records/{record_id}",
    status_code=204,
    summary="逻辑删除一条就业记录",
)
def delete_employment_record(
    record_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    stu_records_dao.delete_record(db, _record_or_404(db, record_id))
    return Response(status_code=204)
