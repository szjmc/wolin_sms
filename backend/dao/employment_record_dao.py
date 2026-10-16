"""
就业记录数据访问层：只负责 employment_records 表的增删改查，不写业务判断
"""
from datetime import datetime

from sqlalchemy import case
from sqlalchemy.orm import Session

from dao.common import clean_text, paginate
from model.employment_record import EmploymentRecord
from model.student import Student


def annualized_salary_expression():
    """
    生成"年薪等价值"的 SQL 表达式，只用于数据库里的排序和筛选，不会修改原始薪资：
    - salary_period = 'MONTH'（月薪）：salary_amount × 12
    - salary_period = 'YEAR'（年薪）：salary_amount

    相当于 SQL：CASE WHEN salary_period = 'MONTH' THEN salary_amount * 12 ELSE salary_amount END
    """
    return case(
        (EmploymentRecord.salary_period == "MONTH", EmploymentRecord.salary_amount * 12),
        else_=EmploymentRecord.salary_amount,
    )


def get_record_by_id(db: Session, record_id: int):
    """根据ID查询一条未删除的就业记录，查不到返回 None"""
    return (
        db.query(EmploymentRecord)
        .filter(EmploymentRecord.id == record_id, EmploymentRecord.is_deleted == 0)
        .first()
    )


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
    min_salary=None,
    max_salary=None,
    min_annualized_salary=None,
    max_annualized_salary=None,
):
    """
    按条件分页查询就业记录，返回 (当前页记录列表, 总条数)。
    - 只返回未删除的记录，并且所属学生也必须未删除
    - min_salary / max_salary：按"原始薪资金额"比较（建议同时指定 salary_period）
    - min_annualized_salary / max_annualized_salary：按"年薪等价值"比较（跨月薪/年薪比较时使用）
    """
    student_no = clean_text(student_no)
    class_no_snapshot = clean_text(class_no_snapshot)
    company_name = clean_text(company_name)
    employment_city = clean_text(employment_city)
    position = clean_text(position)
    salary_period = clean_text(salary_period)

    # 关联学生表：已删除学生的就业记录在普通查询中不展示
    query = (
        db.query(EmploymentRecord)
        .join(Student, Student.id == EmploymentRecord.student_id)
        .filter(EmploymentRecord.is_deleted == 0, Student.is_deleted == 0)
    )
    if student_no is not None:
        query = query.filter(Student.student_no == student_no)
    if class_no_snapshot is not None:
        query = query.filter(EmploymentRecord.class_no_snapshot == class_no_snapshot)
    if company_name is not None:
        query = query.filter(EmploymentRecord.company_name.like(f"%{company_name}%"))
    if employment_city is not None:
        query = query.filter(EmploymentRecord.employment_city.like(f"%{employment_city}%"))
    if position is not None:
        query = query.filter(EmploymentRecord.position.like(f"%{position}%"))
    if salary_period is not None:
        query = query.filter(EmploymentRecord.salary_period == salary_period)
    if min_salary is not None:
        query = query.filter(EmploymentRecord.salary_amount >= min_salary)
    if max_salary is not None:
        query = query.filter(EmploymentRecord.salary_amount <= max_salary)
    if min_annualized_salary is not None:
        query = query.filter(annualized_salary_expression() >= min_annualized_salary)
    if max_annualized_salary is not None:
        query = query.filter(annualized_salary_expression() <= max_annualized_salary)

    query = query.order_by(EmploymentRecord.id.asc())
    return paginate(query, page, page_size)


def list_records_by_student(db: Session, student_id: int, page: int, page_size: int):
    """
    分页查询某个学生的就业历史，返回 (当前页记录列表, 总条数)。
    排序规则：就业开放日期 → Offer 日期 → 记录ID，都按从早到晚。
    """
    query = db.query(EmploymentRecord).filter(
        EmploymentRecord.student_id == student_id,
        EmploymentRecord.is_deleted == 0,
    )

    query = query.order_by(
        EmploymentRecord.employment_open_date.asc(),
        EmploymentRecord.offer_date.asc(),
        EmploymentRecord.id.asc(),
    )
    return paginate(query, page, page_size)


def create_record(db: Session, data: dict):
    """新增一条就业记录（只新增，不会修改该学生的其他就业记录）"""
    record = EmploymentRecord(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_record(db: Session, record: EmploymentRecord, changes: dict):
    """修改一条就业记录：只修改 changes 里出现的字段"""
    for field_name, value in changes.items():
        setattr(record, field_name, value)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record: EmploymentRecord):
    """逻辑删除一条就业记录（不影响该学生的其他就业记录）"""
    record.is_deleted = 1
    record.deleted_at = datetime.now()
    db.commit()


def list_active_records_by_student(db: Session, student_id: int):
    """查询某个学生全部未删除的就业记录（判断就业状态、做 Offer 选择时用）"""
    return (
        db.query(EmploymentRecord)
        .filter(EmploymentRecord.student_id == student_id, EmploymentRecord.is_deleted == 0)
        .order_by(EmploymentRecord.id.asc())
        .all()
    )


def list_accepted_student_ids(db: Session):
    """
    查询所有"有已接受 Offer"的学生ID集合。
    学生的就业状态就是靠它算的：在集合里=已就业，不在=待就业。
    """
    rows = (
        db.query(EmploymentRecord.student_id)
        .join(Student, Student.id == EmploymentRecord.student_id)
        .filter(
            EmploymentRecord.is_deleted == 0,
            Student.is_deleted == 0,
            EmploymentRecord.offer_status == "已接受",
        )
        .distinct()
        .all()
    )
    ids = []
    for row in rows:
        ids.append(row.student_id)
    return ids


def set_offer_status(db: Session, record: EmploymentRecord, status: str):
    """修改一条就业记录的 Offer 状态"""
    record.offer_status = status
    db.commit()
    db.refresh(record)
    return record


def reject_other_offers(db: Session, record: EmploymentRecord):
    """
    选中一条 Offer 之后，把同一学生其他"未删除"的就业记录全部改成"已拒绝"。
    只动其他记录，不动当前这条（当前这条由调用方改成"已接受"）。
    """
    others = (
        db.query(EmploymentRecord)
        .filter(
            EmploymentRecord.student_id == record.student_id,
            EmploymentRecord.id != record.id,
            EmploymentRecord.is_deleted == 0,
        )
        .all()
    )
    now = datetime.now()
    for other in others:
        other.offer_status = "已拒绝"
        other.updated_at = now
    db.commit()
