"""
统计分析接口
============
统一规则：所有统计都只统计"未删除"的数据——
- 学生：is_deleted = 0
- 成绩 / 就业记录：自身 is_deleted = 0，并且所属学生 is_deleted == 0

GET /api/v1/statistics/students/over-age                     年龄大于指定岁数的学生（默认 30）
GET /api/v1/statistics/classes/student-counts                班级总人数、男女生人数
GET /api/v1/statistics/scores/all-at-least                   已有成绩全部 >= 80 的学生
GET /api/v1/statistics/scores/failures                       至少 3 次不及格的学生
GET /api/v1/statistics/scores/class-averages                 每次考核各班平均分
GET /api/v1/statistics/employment/top-salaries               就业薪资前五名（按年薪等价值）
GET /api/v1/statistics/employment/durations                  每条就业记录的就业时长
GET /api/v1/statistics/employment/class-average-durations    班级平均就业时长（按班级快照）
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.common import (
    ERROR_RESPONSES,
    get_current_user,
    calculate_annualized_salary,
    calculate_birth_date_cutoff,
    page_data,
    round_2,
    success,
    to_student_read,
)
from dao import class_dao, statistics_dao, student_dao
from database import get_db
from scheme.common import ApiResponse, PageData
from scheme.statistics import (
    ClassAverageDuration,
    ClassExamAverage,
    ClassStudentCount,
    EmploymentDurationItem,
    StudentFailureSummary,
    TopSalaryItem,
)
from scheme.student import StudentRead

router = APIRouter(prefix="/statistics", tags=["统计分析"], responses=ERROR_RESPONSES, dependencies=[Depends(get_current_user)])


@router.get(
    "/students/over-age",
    response_model=ApiResponse[PageData[StudentRead]],
    summary="年龄大于指定岁数的学生（默认大于 30 岁）",
)
def over_age_students(
    age_gt: int = Query(default=30, ge=0, le=150, description="年龄大于该值，默认 30"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    # 年龄 > age_gt 等价于 出生日期 <= 截止日期（直接比较出生日期，可以用上索引）
    max_birth_date = calculate_birth_date_cutoff(age_gt)
    students, total = student_dao.list_students(db, page, page_size, max_birth_date=max_birth_date)

    items = []
    for student in students:
        items.append(to_student_read(student))
    return success(page_data(items, total, page, page_size))


@router.get(
    "/classes/student-counts",
    response_model=ApiResponse[list[ClassStudentCount]],
    summary="各班级学生总人数及男女生人数",
)
def class_student_counts(
    class_id: int | None = Query(default=None, description="班级ID，不传则统计全部班级"),
    db: Session = Depends(get_db),
):
    # 第 1 步：确定要统计哪些班级
    if class_id is not None:
        class_info = class_dao.get_class_by_id(db, class_id)
        if class_info is None:
            raise HTTPException(status_code=404, detail="班级不存在或已删除")
        class_list = [class_info]
    else:
        class_list = class_dao.list_all_classes(db)

    # 第 2 步：一条 SQL 查出"每个班级、每种性别"的未删除学生人数
    rows = statistics_dao.count_students_group_by_class_and_gender(db)

    # 第 3 步：整理成字典，结构为 {班级ID: {"男": 人数, "女": 人数, "其他": 人数}}
    count_map = {}
    for row in rows:
        if row.class_id not in count_map:
            count_map[row.class_id] = {"男": 0, "女": 0, "其他": 0}
        count_map[row.class_id][row.gender] = row.student_count

    # 第 4 步：按班级组装结果，没有学生的班级人数都是 0
    result = []
    for class_info in class_list:
        gender_counts = count_map.get(class_info.id)
        if gender_counts is None:
            gender_counts = {"男": 0, "女": 0, "其他": 0}

        male_count = gender_counts["男"]
        female_count = gender_counts["女"]
        other_count = gender_counts["其他"]

        item = ClassStudentCount(
            class_id=class_info.id,
            class_no=class_info.class_no,
            class_name=class_info.class_name,
            total_students=male_count + female_count + other_count,
            male_count=male_count,
            female_count=female_count,
            other_count=other_count,
        )
        result.append(item)
    return success(result)


@router.get(
    "/scores/all-at-least",
    response_model=ApiResponse[list[StudentRead]],
    summary="已有成绩全部达标的学生（默认所有有效成绩 >= 80）",
)
def all_scores_at_least(
    min_score: Decimal = Query(default=Decimal("80"), ge=0, le=100, description="达标分数线，默认 80"),
    db: Session = Depends(get_db),
):
    # 规则：至少有一条有效成绩，并且所有有效成绩都 >= min_score
    # 没有成绩的学生不算达标；只要有一条成绩低于分数线（如 79 分）就不达标
    student_ids = statistics_dao.list_student_ids_all_scores_at_least(db, min_score)
    students = student_dao.list_students_by_ids(db, student_ids)

    result = []
    for student in students:
        result.append(to_student_read(student))
    return success(result)


@router.get(
    "/scores/failures",
    response_model=ApiResponse[list[StudentFailureSummary]],
    summary="多次不及格的学生（默认至少 3 次低于 60 分）",
)
def score_failures(
    fail_score: Decimal = Query(default=Decimal("60"), ge=0, le=100, description="不及格线：低于该分数算不及格，默认 60"),
    min_fail_count: int = Query(default=3, ge=1, description="至少不及格的次数，默认 3"),
    db: Session = Depends(get_db),
):
    # 第 1 步：查出每个学生的不及格次数（已经按次数从多到少排好序）
    rows = statistics_dao.list_failure_counts(db, fail_score, min_fail_count)

    # 第 2 步：查出这些学生的档案，整理成字典 {学生ID: 学生对象}
    student_ids = []
    for row in rows:
        student_ids.append(row.student_id)
    students = student_dao.list_students_by_ids(db, student_ids)
    student_map = {}
    for student in students:
        student_map[student.id] = student

    # 第 3 步：查出全部班级，整理成字典 {班级ID: 班级对象}，用来带出班级编号和名称
    class_map = {}
    for class_info in class_dao.list_all_classes(db):
        class_map[class_info.id] = class_info

    # 第 4 步：按不及格次数的顺序组装结果
    result = []
    for row in rows:
        student = student_map.get(row.student_id)
        if student is None:
            continue
        class_info = class_map.get(student.class_id)
        item = StudentFailureSummary(
            student_id=student.id,
            student_no=student.student_no,
            name=student.name,
            class_id=student.class_id,
            class_no=class_info.class_no if class_info else "",
            class_name=class_info.class_name if class_info else "",
            fail_count=row.fail_count,
        )
        result.append(item)
    return success(result)


@router.get(
    "/scores/class-averages",
    response_model=ApiResponse[list[ClassExamAverage]],
    summary="每次考核各班级的平均分",
)
def class_exam_averages(
    exam_no: int | None = Query(default=None, ge=1, description="考核序次，不传则统计全部考核"),
    class_id: int | None = Query(default=None, description="班级ID，不传则统计全部班级"),
    db: Session = Depends(get_db),
):
    rows = statistics_dao.list_class_exam_averages(db, exam_no=exam_no, class_id=class_id)

    result = []
    for row in rows:
        item = ClassExamAverage(
            class_id=row.class_id,
            class_no=row.class_no,
            class_name=row.class_name,
            exam_no=row.exam_no,
            average_score=round_2(row.average_score),
            sample_count=row.sample_count,
        )
        result.append(item)
    return success(result)


@router.get(
    "/employment/top-salaries",
    response_model=ApiResponse[list[TopSalaryItem]],
    summary="就业薪资排行（默认前 5 名，按年薪等价值排序，返回原始薪资和周期）",
)
def top_salaries(
    limit: int = Query(default=5, ge=1, le=100, description="取前几名，默认 5"),
    db: Session = Depends(get_db),
):
    records = statistics_dao.list_top_salary_records(db, limit)

    # 一次性查出这些记录所属学生的档案，用来带出学历（避免每条记录查一次数据库）
    student_ids = []
    for record in records:
        student_ids.append(record.student_id)
    student_map = {}
    for student in student_dao.list_students_by_ids(db, student_ids):
        student_map[student.id] = student

    result = []
    rank = 0
    for record in records:
        rank = rank + 1
        student = student_map.get(record.student_id)
        item = TopSalaryItem(
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
            annualized_salary=calculate_annualized_salary(record.salary_amount, record.salary_period),
        )
        result.append(item)
    return success(result)


@router.get(
    "/employment/durations",
    response_model=ApiResponse[list[EmploymentDurationItem]],
    summary="每条就业记录的就业时长（Offer 日期 - 就业开放日期）",
)
def employment_durations(
    student_id: int | None = Query(default=None, description="学生ID"),
    class_id: int | None = Query(default=None, description="班级ID（按就业记录中的班级编号快照统计）"),
    db: Session = Depends(get_db),
):
    # 指定了学生时，学生必须存在且未删除
    if student_id is not None:
        if student_dao.get_student_by_id(db, student_id) is None:
            raise HTTPException(status_code=404, detail="学生不存在或已删除")

    # 指定了班级时，把班级ID换成班级编号，按快照口径筛选
    class_no = None
    if class_id is not None:
        class_info = class_dao.get_class_by_id(db, class_id)
        if class_info is None:
            raise HTTPException(status_code=404, detail="班级不存在或已删除")
        class_no = class_info.class_no

    # 只查两个日期都有值的记录（缺少任何一个日期都无法计算时长）
    records = statistics_dao.list_records_with_both_dates(db, student_id=student_id, class_no_snapshot=class_no)

    result = []
    for record in records:
        # 就业时长 = Offer 日期 - 就业开放日期（自然日天数）
        duration_days = (record.offer_date - record.employment_open_date).days
        item = EmploymentDurationItem(
            employment_record_id=record.id,
            student_id=record.student_id,
            student_name_snapshot=record.student_name_snapshot,
            class_no_snapshot=record.class_no_snapshot,
            company_name=record.company_name,
            employment_open_date=record.employment_open_date,
            offer_date=record.offer_date,
            duration_days=duration_days,
        )
        result.append(item)
    return success(result)


@router.get(
    "/employment/class-average-durations",
    response_model=ApiResponse[list[ClassAverageDuration]],
    summary="班级平均就业时长（按就业记录中的班级编号快照统计）",
)
def class_average_durations(
    class_id: int | None = Query(default=None, description="班级ID，不传则统计全部班级"),
    db: Session = Depends(get_db),
):
    # 指定了班级时，把班级ID换成班级编号
    class_no = None
    if class_id is not None:
        class_info = class_dao.get_class_by_id(db, class_id)
        if class_info is None:
            raise HTTPException(status_code=404, detail="班级不存在或已删除")
        class_no = class_info.class_no

    # 第 1 步：查出两个日期都有值的有效就业记录（已按班级快照排好序）
    records = statistics_dao.list_records_with_both_dates(db, class_no_snapshot=class_no)

    # 第 2 步：按班级快照分组累加，结构为 {班级编号: {"total_days": 总天数, "count": 记录数}}
    group_map = {}
    for record in records:
        key = record.class_no_snapshot
        duration_days = (record.offer_date - record.employment_open_date).days
        if key not in group_map:
            group_map[key] = {"total_days": 0, "count": 0}
        group_map[key]["total_days"] = group_map[key]["total_days"] + duration_days
        group_map[key]["count"] = group_map[key]["count"] + 1

    # 第 3 步：计算每个班级的平均天数
    result = []
    for class_no_snapshot, group in group_map.items():
        average_days = round_2(Decimal(group["total_days"]) / Decimal(group["count"]))
        item = ClassAverageDuration(
            class_no_snapshot=class_no_snapshot,
            record_count=group["count"],
            average_duration_days=average_days,
        )
        result.append(item)
    return success(result)
