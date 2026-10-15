"""就业记录数据访问层。

本层保留小组原函数名，负责就业记录的可见性联表、组合筛选、分页 CRUD 及筛选项读取；
跨字段日期规则和响应派生字段仍由 API 层处理。
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from model.stu_records_model import EmploymentRecord
from model.students_model import StudentDB


# [修改说明] 原代码：通过 EmploymentRecord.student.has(...) 依赖两端不完整的 ORM relationship；修改原因：Student 模型没有对应 back_populates，mapper 初始化即可能失败；修改为：所有可见就业查询显式联接 students，并同时过滤就业记录和学生的逻辑删除标记。
def _visible_query(db: Session):
    return (
        db.query(EmploymentRecord)
        .join(StudentDB, StudentDB.id == EmploymentRecord.student_id)
        .filter(
            EmploymentRecord.is_deleted == 0,
            StudentDB.is_deleted == 0,
        )
    )


def annualized_salary_expression():
    """保留小组原公共函数名：返回可用于筛选的年薪等值表达式。"""
    return case(
        (
            EmploymentRecord.salary_period == "MONTH",
            EmploymentRecord.salary_amount * 12,
        ),
        else_=EmploymentRecord.salary_amount,
    )


def get_record(db: Session, record_id: int):
    """按 ID 查询可见记录；所属学生已删除时记录也不可见。"""
    return _visible_query(db).filter(EmploymentRecord.id == record_id).first()


# 保留小组原函数名，供尚未迁移的调用方兼容。
def get_record_by_id(db: Session, record_id: int):
    return get_record(db, record_id)


def create_record(db: Session, data: dict):
    """新增就业记录。"""
    record = EmploymentRecord(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# [修改说明] 原代码：列表只支持少量字段，文本值不清洗，薪资表达式也未覆盖前端统一月薪/年薪口径；修改原因：空白筛选、综合检索、毕业年限和跨周期薪资筛选不可用；修改为：在原分页函数中补齐全部核心及前端筛选条件，并保留原始薪资与年化薪资两套兼容参数。
def list_records(
    db: Session,
    page: int,
    page_size: int,
    student_no: str | None = None,
    class_no_snapshot: str | None = None,
    company_name: str | None = None,
    employment_city: str | None = None,
    position: str | None = None,
    salary_period: str | None = None,
    min_salary: Decimal | None = None,
    max_salary: Decimal | None = None,
    min_annualized_salary: Decimal | None = None,
    max_annualized_salary: Decimal | None = None,
    *,
    q: str | None = None,
    class_no: str | None = None,
    salary_basis: str | None = None,
    graduation_before_or_on: date | None = None,
    graduation_after: date | None = None,
):
    """分页查询全部可见就业记录，所有筛选按 AND 组合。"""
    q = clean_text(q)
    student_no = clean_text(student_no)
    # class_no 是新接口内的简写；class_no_snapshot 保留原 DAO 关键字兼容。
    class_no = clean_text(class_no if class_no is not None else class_no_snapshot)
    company_name = clean_text(company_name)
    employment_city = clean_text(employment_city)
    position = clean_text(position)
    salary_period = clean_text(salary_period)
    salary_basis = clean_text(salary_basis)

    query = _visible_query(db)

    if q is not None:
        keyword = f"%{q}%"
        query = query.filter(
            or_(
                StudentDB.student_no.like(keyword),
                EmploymentRecord.student_name_snapshot.like(keyword),
                EmploymentRecord.company_name.like(keyword),
            )
        )
    if student_no is not None:
        query = query.filter(StudentDB.student_no == student_no)
    if class_no is not None:
        query = query.filter(EmploymentRecord.class_no_snapshot == class_no)
    if company_name is not None:
        query = query.filter(EmploymentRecord.company_name.like(f"%{company_name}%"))
    if employment_city is not None:
        query = query.filter(EmploymentRecord.employment_city.like(f"%{employment_city}%"))
    if position is not None:
        query = query.filter(EmploymentRecord.position.like(f"%{position}%"))
    if salary_period is not None:
        query = query.filter(EmploymentRecord.salary_period == salary_period)

    annualized = annualized_salary_expression()
    if salary_basis == "MONTH":
        selected_salary = annualized / 12
    elif salary_basis == "YEAR":
        selected_salary = annualized
    else:
        selected_salary = EmploymentRecord.salary_amount

    if min_salary is not None:
        query = query.filter(selected_salary >= min_salary)
    if max_salary is not None:
        query = query.filter(selected_salary <= max_salary)
    if min_annualized_salary is not None:
        query = query.filter(annualized >= min_annualized_salary)
    if max_annualized_salary is not None:
        query = query.filter(annualized <= max_annualized_salary)

    if graduation_before_or_on is not None:
        query = query.filter(
            EmploymentRecord.past_graduation_date.is_not(None),
            EmploymentRecord.past_graduation_date <= graduation_before_or_on,
        )
    if graduation_after is not None:
        query = query.filter(
            EmploymentRecord.past_graduation_date.is_not(None),
            EmploymentRecord.past_graduation_date > graduation_after,
        )

    query = query.order_by(EmploymentRecord.id.asc())
    return paginate(query, page, page_size)


def list_records_by_student(
    db: Session,
    student_id: int,
    page: int,
    page_size: int,
):
    """按学生分页查询就业历史，依就业开放日期和 ID 升序。"""
    query = (
        _visible_query(db)
        .filter(EmploymentRecord.student_id == student_id)
        .order_by(
            EmploymentRecord.employment_open_date.asc(),
            EmploymentRecord.id.asc(),
        )
    )
    return paginate(query, page, page_size)


def list_records_by_class_no(
    db: Session,
    class_no: str,
    page: int,
    page_size: int,
):
    """按创建时班号快照分页查询，学生后来转班不改变历史归属。"""
    query = (
        _visible_query(db)
        .filter(EmploymentRecord.class_no_snapshot == class_no)
        .order_by(EmploymentRecord.id.asc())
    )
    return paginate(query, page, page_size)


def update_record(db: Session, record: EmploymentRecord, changes: dict):
    """只写入 PATCH 中实际出现的字段。"""
    for field_name, value in changes.items():
        setattr(record, field_name, value)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record: EmploymentRecord):
    """逻辑删除单条就业记录，不影响该学生其他经历。"""
    record.is_deleted = 1
    record.deleted_at = datetime.now()
    db.commit()


def list_filter_options(db: Session):
    """返回可见记录中非空、去重并升序排列的城市与岗位。"""
    base_filters = (
        EmploymentRecord.is_deleted == 0,
        StudentDB.is_deleted == 0,
    )
    cities = (
        db.query(EmploymentRecord.employment_city)
        .join(StudentDB, StudentDB.id == EmploymentRecord.student_id)
        .filter(
            *base_filters,
            EmploymentRecord.employment_city.is_not(None),
            EmploymentRecord.employment_city != "",
        )
        .distinct()
        .order_by(EmploymentRecord.employment_city.asc())
        .all()
    )
    positions = (
        db.query(EmploymentRecord.position)
        .join(StudentDB, StudentDB.id == EmploymentRecord.student_id)
        .filter(
            *base_filters,
            EmploymentRecord.position.is_not(None),
            EmploymentRecord.position != "",
        )
        .distinct()
        .order_by(EmploymentRecord.position.asc())
        .all()
    )
    return [row[0] for row in cities], [row[0] for row in positions]
