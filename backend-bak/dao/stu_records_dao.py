from datetime import datetime

from sqlalchemy import case
from sqlalchemy.orm import Session

from model.stu_records_model import EmploymentRecord
from model.student import Student

#年薪转换为月薪
def annualized_salary_expression():
    return case(
        (EmploymentRecord.salary_period == "MONTH", EmploymentRecord.salary_amount * 12),
        else_=EmploymentRecord.salary_amount,
    )

#查询就业纪录
def get_record_by_id(db: Session, record_id: int):
    return (
        db.query(EmploymentRecord)
        .filter(EmploymentRecord.id == record_id, EmploymentRecord.is_deleted == 0)
        .first()
    )

#按照条件查询
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

# 关联学生表：已删除学生的就业记录在普通查询中不展示
    query = (
        db.query(EmploymentRecord)
        .filter(
            EmploymentRecord.is_deleted == 0,
            EmploymentRecord.student.has(
                Student.is_deleted == 0
            )
        )
    )
    if student_no:
        query = query.filter(EmploymentRecord.student.has(Student.student_no == student_no))
    if class_no_snapshot:
        query = query.filter(EmploymentRecord.class_no_snapshot == class_no_snapshot)
    if company_name:
        query = query.filter(EmploymentRecord.company_name.like(f"%{company_name}%"))
    if employment_city:
        query = query.filter(EmploymentRecord.employment_city.like(f"%{employment_city}%"))
    if position:
        query = query.filter(EmploymentRecord.position.like(f"%{position}%"))
    if salary_period:
        query = query.filter(EmploymentRecord.salary_period == salary_period)
    if min_salary is not None:
        query = query.filter(EmploymentRecord.salary_amount >= min_salary)
    if max_salary is not None:
        query = query.filter(EmploymentRecord.salary_amount <= max_salary)
    if min_annualized_salary is not None:
        query = query.filter(annualized_salary_expression() >= min_annualized_salary)
    if max_annualized_salary is not None:
        query = query.filter(annualized_salary_expression() <= max_annualized_salary)

    total = query.count()
    records = (
        query.order_by(EmploymentRecord.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return records, total

#查询就业历史
def list_records_by_student(db: Session, student_id: int, page: int, page_size: int):
    query = db.query(EmploymentRecord).filter(
        EmploymentRecord.student_id == student_id,
        EmploymentRecord.is_deleted == 0,
    )

    total = query.count()
    records = (
        query.order_by(
            EmploymentRecord.employment_open_date.asc(),
            EmploymentRecord.offer_date.asc(),
            EmploymentRecord.id.asc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return records, total

#新增就业内容
def create_record(db: Session, data: dict):
    record = EmploymentRecord(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

#修改就业内容
def update_record(db: Session, record: EmploymentRecord, changes: dict):
    for field_name, value in changes.items():
        setattr(record, field_name, value)
    db.commit()
    db.refresh(record)
    return record

#逻辑删除
def delete_record(db: Session, record: EmploymentRecord):
    record.is_deleted = 1
    record.deleted_at = datetime.now()
    db.commit()