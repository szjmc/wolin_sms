"""统计分析接口。

所有结果只统计有效主记录；成绩、就业记录还同时要求所属学生未删除。空结果正常返回
空列表，不把“暂时没有数据”误报为 404。
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.common import (
    ERROR_RESPONSES,
    calculate_annualized_salary,
    calculate_birth_date_cutoff,
    page_data,
    round_2,
    success,
    to_student_read,
)
from dao import class_info_dao, statistics as statistics_dao, students_dao
from database import get_db
from scheme.common import ApiResponse, PageData
from scheme.statistics import (
    ClassAverageDuration,
    ClassExamAverage,
    ClassStudentCount,
    EmploymentDurationItem,
    StudentFailureSummary,
    SystemOverview,
    TopSalaryItem,
)
from scheme.students import StudentRead


# [修改说明] 原代码：八条路由使用 /basic、/score 等旧路径，直接返回 code=200 临时字典且空结果抛 404；修改原因：与统一 V1 响应、完整后端及统计页面契约不一致；修改为：保留 api/statistics.py 和 /statistics 前缀，补齐参数化八个核心接口及工作台 overview，全部声明响应模型。
router = APIRouter(
    prefix="/statistics",
    tags=["统计分析"],
    responses=ERROR_RESPONSES,
)


def _student_read(db: Session, student) -> StudentRead:
    class_info = class_info_dao.get_class_by_id(db, student.class_id)
    return to_student_read(student, class_info)


@router.get(
    "/overview",
    response_model=ApiResponse[SystemOverview],
    summary="工作台有效数据总览",
)
def system_overview(db: Session = Depends(get_db)):
    return success(
        SystemOverview.model_validate(
            statistics_dao.get_system_overview_counts(db)
        )
    )


@router.get(
    "/students/over-age",
    response_model=ApiResponse[PageData[StudentRead]],
    summary="年龄大于指定岁数的学生",
)
def over_age_students(
    age_gt: int = Query(default=30, ge=0, le=150),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    max_birth_date = calculate_birth_date_cutoff(age_gt)
    students, total = students_dao.list_students(
        db,
        page,
        page_size,
        max_birth_date=max_birth_date,
    )
    items = [_student_read(db, student) for student in students]
    return success(page_data(items, total, page, page_size))


@router.get(
    "/classes/student-counts",
    response_model=ApiResponse[list[ClassStudentCount]],
    summary="各班级学生总人数及性别分布",
)
def class_student_counts(
    class_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    if class_id is not None:
        class_info = class_info_dao.get_class_by_id(db, class_id)
        if class_info is None:
            raise HTTPException(status_code=404, detail="班级不存在或已删除")
        classes = [class_info]
    else:
        classes = class_info_dao.list_all_classes(db)

    rows = statistics_dao.count_students_group_by_class_and_gender(
        db, class_id=class_id
    )
    count_map: dict[int, dict[str, int]] = {}
    for row in rows:
        count_map.setdefault(
            row.class_id,
            {"男": 0, "女": 0, "其他": 0},
        )[row.gender] = int(row.student_count)

    result = []
    for class_info in classes:
        gender_counts = count_map.get(
            class_info.id,
            {"男": 0, "女": 0, "其他": 0},
        )
        male_count = gender_counts.get("男", 0)
        female_count = gender_counts.get("女", 0)
        other_count = gender_counts.get("其他", 0)
        result.append(
            ClassStudentCount(
                class_id=class_info.id,
                class_no=class_info.class_no,
                class_name=class_info.class_name,
                total_students=male_count + female_count + other_count,
                male_count=male_count,
                female_count=female_count,
                other_count=other_count,
            )
        )
    return success(result)


@router.get(
    "/scores/all-at-least",
    response_model=ApiResponse[list[StudentRead]],
    summary="已有成绩全部达到指定分数的学生",
)
def all_scores_at_least(
    min_score: Decimal = Query(default=Decimal("80"), ge=0, le=100),
    db: Session = Depends(get_db),
):
    student_ids = statistics_dao.list_student_ids_all_scores_at_least(
        db, min_score
    )
    students = students_dao.list_students_by_ids(db, student_ids)
    return success([_student_read(db, student) for student in students])


@router.get(
    "/scores/failures",
    response_model=ApiResponse[list[StudentFailureSummary]],
    summary="多次不及格学生",
)
def score_failures(
    fail_score: Decimal = Query(default=Decimal("60"), ge=0, le=100),
    min_fail_count: int = Query(default=3, ge=1),
    db: Session = Depends(get_db),
):
    rows = statistics_dao.list_failure_counts(
        db, fail_score, min_fail_count
    )
    student_ids = [row.student_id for row in rows]
    student_map = {
        student.id: student
        for student in students_dao.list_students_by_ids(db, student_ids)
    }
    class_map = {
        class_info.id: class_info
        for class_info in class_info_dao.list_all_classes(db)
    }

    result = []
    for row in rows:
        student = student_map.get(row.student_id)
        if student is None:
            continue
        class_info = class_map.get(student.class_id)
        result.append(
            StudentFailureSummary(
                student_id=student.id,
                student_no=student.student_no,
                name=student.name,
                class_id=student.class_id,
                class_no=class_info.class_no if class_info else "",
                class_name=class_info.class_name if class_info else "",
                fail_count=int(row.fail_count),
            )
        )
    return success(result)


@router.get(
    "/scores/class-averages",
    response_model=ApiResponse[list[ClassExamAverage]],
    summary="每次考核各班级平均分与样本量",
)
def class_exam_averages(
    exam_no: int | None = Query(default=None, ge=1),
    class_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    rows = statistics_dao.list_class_exam_averages(
        db,
        exam_no=exam_no,
        class_id=class_id,
    )
    return success(
        [
            ClassExamAverage(
                class_id=row.class_id,
                class_no=row.class_no,
                class_name=row.class_name,
                exam_no=row.exam_no,
                average_score=round_2(row.average_score),
                sample_count=int(row.sample_count),
            )
            for row in rows
        ]
    )


@router.get(
    "/employment/top-salaries",
    response_model=ApiResponse[list[TopSalaryItem]],
    summary="就业薪资排行（按年薪等价值）",
)
def top_salaries(
    limit: int = Query(default=5, ge=1, le=100),
    db: Session = Depends(get_db),
):
    records = statistics_dao.list_top_salary_records(db, limit)
    student_map = {
        student.id: student
        for student in students_dao.list_students_by_ids(
            db, [record.student_id for record in records]
        )
    }
    result = []
    for rank, record in enumerate(records, start=1):
        student = student_map.get(record.student_id)
        result.append(
            TopSalaryItem(
                rank=rank,
                employment_record_id=record.id,
                student_id=record.student_id,
                student_name_snapshot=record.student_name_snapshot,
                class_no_snapshot=record.class_no_snapshot,
                education=student.education if student else None,
                company_name=record.company_name,
                employment_city=record.employment_city,
                position=record.position,
                offer_date=record.offer_date,
                salary_amount=record.salary_amount,
                salary_period=record.salary_period,
                annualized_salary=calculate_annualized_salary(
                    record.salary_amount, record.salary_period
                ),
            )
        )
    return success(result)


@router.get(
    "/employment/durations",
    response_model=ApiResponse[list[EmploymentDurationItem]],
    summary="每条就业记录的求职周期",
)
def employment_durations(
    student_id: int | None = Query(default=None, ge=1),
    class_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    if (
        student_id is not None
        and students_dao.get_student_by_id(db, student_id) is None
    ):
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    class_no = None
    if class_id is not None:
        class_info = class_info_dao.get_class_by_id(db, class_id)
        if class_info is None:
            raise HTTPException(status_code=404, detail="班级不存在或已删除")
        class_no = class_info.class_no

    records = statistics_dao.list_records_with_both_dates(
        db,
        student_id=student_id,
        class_no_snapshot=class_no,
    )
    return success(
        [
            EmploymentDurationItem(
                employment_record_id=record.id,
                student_id=record.student_id,
                student_name_snapshot=record.student_name_snapshot,
                class_no_snapshot=record.class_no_snapshot,
                company_name=record.company_name,
                employment_open_date=record.employment_open_date,
                offer_date=record.offer_date,
                duration_days=(
                    record.offer_date - record.employment_open_date
                ).days,
            )
            for record in records
        ]
    )


@router.get(
    "/employment/class-average-durations",
    response_model=ApiResponse[list[ClassAverageDuration]],
    summary="班级平均求职周期（按班号快照）",
)
def class_average_durations(
    class_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    class_no = None
    if class_id is not None:
        class_info = class_info_dao.get_class_by_id(db, class_id)
        if class_info is None:
            raise HTTPException(status_code=404, detail="班级不存在或已删除")
        class_no = class_info.class_no

    records = statistics_dao.list_records_with_both_dates(
        db,
        class_no_snapshot=class_no,
    )
    groups: dict[str, dict[str, int]] = {}
    for record in records:
        group = groups.setdefault(
            record.class_no_snapshot,
            {"total_days": 0, "count": 0},
        )
        group["total_days"] += (
            record.offer_date - record.employment_open_date
        ).days
        group["count"] += 1

    result = []
    for class_no_snapshot, group in groups.items():
        result.append(
            ClassAverageDuration(
                class_no_snapshot=class_no_snapshot,
                record_count=group["count"],
                average_duration_days=round_2(
                    Decimal(group["total_days"])
                    / Decimal(group["count"])
                ),
            )
        )
    return success(result)
