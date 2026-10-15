from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from dao import statistics

router = APIRouter(prefix="/statistics", tags=["统计分析"])

@router.get("/basic/over-30", summary="查询所有超过30岁的学员")
def students_over_30(db: Session = Depends(get_db)):
    return statistics.get_students_over_30(db)


@router.get("/basic/class-gender", summary="统计每个班级的人数及男、女生人数")
def class_gender_count(db: Session = Depends(get_db)):
    # 用 CASE WHEN 分别累加男、女生人数
    return statistics.get_class_gender_num(db)


# ============================================================
# 二、成绩统计
# ============================================================
@router.get("/score/always-over-80", summary="每次考试成绩都在80分以上的学生")
def always_over_80(db: Session = Depends(get_db)):
    return statistics.get_score_gt_80_stu(db)


@router.get("/score/fail-twice", summary="有两次及以上不及格的学生（姓名、班级、不及格成绩）")
def fail_twice(db: Session = Depends(get_db)):
    return statistics.fail_twice(db)



@router.get("/score/class-average", summary="每次考试每个班级的平均分（从高到低）")
def class_average_per_exam(db: Session = Depends(get_db)):
    return statistics.class_average_per_exam(db)

# ============================================================
# 三、就业统计
# ============================================================
@router.get("/employment/top5-salary", summary="就业薪资最高的前五名学生")
def top5_salary(db: Session = Depends(get_db)):
    return statistics.top5_salary(db)


@router.get("/employment/duration", summary="统计每个学生的就业时长（天）")
def employment_duration(db: Session = Depends(get_db)):
    return statistics.employment_duration(db)


@router.get("/employment/class-avg-duration", summary="统计每个班级的平均就业时长（天）")
def class_avg_duration(db: Session = Depends(get_db)):
    return statistics.class_avg_duration(db)