
from fastapi import Depends,HTTPException
from sqlalchemy import func, case, text
from sqlalchemy.orm import Session
from database import get_db
from model.students import students
from model.classes import classes
from model.scores import scores
from model.teachers import teachers
from model.employment_records import employment_records
from model.student_past_experiences import StudentPastExperience
from model import class_teacher_relations
from pydantic import BaseModel
from scheme.student import StudentRead



# 查询所有超过30岁的学员
def get_students_over_30(db: Session = Depends(get_db)):

    student = (db.query(students).filter(students.is_deleted==False, func.TIMESTAMPDIFF(text("YEAR"), students.birth_date, func.now()) > 30)
        .order_by(students.birth_date.desc()).all())
    data = [StudentRead.model_validate(stu).model_dump() for stu in student]
    if not data:
        raise HTTPException(404,detail="找不到数据")
    return {"code": 200, "message": "查询成功", "total": len(data), "data": data}

# @router.get("/statistics/class-gender",summary="统计每个班级的人数及男、女生人数")
# def get_class_gender_num(db:Session=Depends(get_db)):
#     case_male = case((Student.gender == "男", 1), else_=0)
#     case_female = case((Student.gender == "女", 1), else_=0)
#     res=(db.query(Student.class_id.label("class_id"),func.count(Student.stu_id).label("total"),
#                   func.sum(case_male).label("male_count"),func.sum(case_female).label("female_count"))
#           .filter(Student.is_deleted.is_(False)).group_by(Student.class_id).all())
#
#     return {
#         "code": 200,
#         "data": [
#             {
#                 "class_room": r.class_room.class_name,
#                 "total": r.total,
#                 "male_count": r.male_count,
#                 "female_count": r.female_count,
#             }
#             for r in res
#         ],
#     }

# 统计每个班级的人数及男、女生人数
def get_class_gender_num(db:Session=Depends(get_db)):
    case_male = case((students.gender == "男", 1), else_=0)
    case_female = case((students.gender == "女", 1), else_=0)
    res=(db.query(students.class_id.label("class_id"),classes.class_name.label("class_name"),func.count(students.id).label("total"),
                  func.sum(case_male).label("male_count"),func.sum(case_female).label("female_count"))
         .join(classes, students.class_id == classes.id).filter(students.is_deleted==False)
         .group_by(students.class_id,classes.class_name).all())
    data=[
            {
                "class_room": r.class_name,
                "total": r.total,
                "male_count": r.male_count,
                "female_count": r.female_count,
            }
            for r in res
        ]
    if not data:
        raise HTTPException(404,detail="找不到数据")
    return {
        "code": 200,"message": "查询成功", "data": data
    }

# 每次考试成绩都在80分以上的学生，输出学生编号、姓名、成绩
def get_score_gt_80_stu(db: Session = Depends(get_db)):
    s_id=db.query(scores.student_id).group_by(scores.student_id).having(func.min(scores.score)>80).all()
    l_st=[s.student_id for s in s_id]
    res=(db.query(students.id.label("student_id"),students.name.label("student_name"),func.group_concat(scores.score).label("score"))
         .join(scores, scores.student_id == students.id).filter(students.id.in_(l_st),students.is_deleted==False).all())

    data=[{
        "student_id": r.student_id,
        "student_name": r.student_name,
        "score": r.score,
    } for r in res
    ]
    if not data:
        raise HTTPException(404,detail="找不到数据")
    return {"code": 200, "message": "查询成功", "data": data}


# 查询有两次以上不及格的学⽣的姓名，班级和不及格成绩o
def fail_twice(db: Session = Depends(get_db)):
    result = []
    case_fail=case((scores.score < 60, 1), else_=0)
    s_c = (db.query(scores.student_id.label("student_id"),students.name.label("student_name"),
            classes.class_name.label("class_name"),func.sum(case_fail).label("fail_count"))
        .join(students, students.id == scores.student_id).join(classes, students.class_id == classes.id).filter(students.is_deleted==False,scores.is_deleted==False)
        .group_by(scores.student_id, students.name, classes.class_name).having(func.sum(case_fail) > 2)  # >2 代表3次及以上；需要2次及以上改成 >=2
        .all())
    if not s_c:
        raise HTTPException(404,detail="找不到数据")
    for sc in s_c:
        fail_scores=db.query(scores.score).filter(scores.student_id==sc.student_id,scores.score<60).all()
        result.append(
            {
                "name":sc.student_name,
                "class_room": sc.class_name,
                "fail_scores":[f.score for f in fail_scores]
            }
        )
    return {"code": 200, "message": "查询成功", "data": result}


# 统计每次考试每个班级的平均分，按照从⾼到低排序
def class_average_per_exam(db: Session = Depends(get_db)):
    rows = (db.query(scores.exam_no.label("exam_seq"),classes.class_no.label("class_no"),
            func.avg(scores.score).label("avg_score"),func.count(scores.student_id).label("student_count"))
        .join(students, scores.student_id == students.id).join(classes,classes.id==students.class_id)
        .filter(students.is_deleted==False,scores.is_deleted==False,classes.is_deleted==False)
        .group_by(scores.exam_no, classes.class_no).order_by(scores.exam_no.asc(), func.avg(scores.score).desc()).all())
    if not rows:
        raise HTTPException(404,detail="找不到数据")
    return {
        "code": 200,"message": "查询成功",
        "data": [
            {
                "class_no": r.class_no,
                "exam_seq": r.exam_seq,
                "avg_score": round(float(r.avg_score), 2),
                "student_count": int(r.student_count),
            }
            for r in rows
        ],
    }


# 统计就业薪资最⾼的前五名学⽣的姓名，班级和就业时间，就业公司
def top5_salary(db: Session = Depends(get_db)):
    case_salary=case((employment_records.salary_period=="year",employment_records.salary_amount),
                     else_=employment_records.salary_amount*12)
    emps = (db.query(employment_records).filter(employment_records.salary_amount.isnot(None))
        .order_by(case_salary.desc()).limit(5).all())
    if not emps:
        raise HTTPException(404,detail="找不到数据")
    return {
        "code": 200, "message": "查询成功",
        "data": [
            {
                "stu_id": e.student_id,
                "name": e.student_name_snapshot,
                "class_room": e.class_no_snapshot,
                "employment_time": e.offer_date.strftime("%Y-%m-%d") if e.offer_date else None,
                "company": e.company_name,
                "position": e.position
            }
            for e in emps
        ],
    }

# 统计每个学⽣的就业时⻓（offer下发时间-就业开放时间）
def employment_duration(db: Session = Depends(get_db)):
    """
    就业时长 = offer下发时间 - 就业开放时间，单位：天。
    缺少任一时间（尚未拿到 offer）的学生，duration 返回 None，不参与时长计算。
    """
    rows = (db.query(students.id.label("student_id"),students.name.label("student_name"),
        func.datediff(employment_records.offer_date,employment_records.employment_open_date).label("duration"))
        .join(employment_records, students.id == employment_records.student_id)
        .filter(students.is_deleted==False,employment_records.is_deleted==False).all())
    data = [
        {
            "student_id": r.student_id,
            "student_name": r.student_name,
            "duration": int(r.duration) if r.duration is not None else None
        }
        for r in rows
    ]
    if not data:
        raise HTTPException(404,detail="找不到数据")
    return {"code": 200, "message": "查询成功", "data": data}


# ）
# 统计每个班级的平均就业时⻓（只统计进⼊就业阶段的学⽣，也就是有就业开放时间）
def class_avg_duration(db: Session = Depends(get_db)):
    """
    只统计进入就业阶段（有就业开放时间）的学生；
    平均时长只对同时具备开放时间和 offer 时间的学生求平均，
    仍在求职（暂无 offer）的学生在未完成人数中体现，保证口径透明。
    """

    emps = (db.query(employment_records.class_no_snapshot,func.avg(func.datediff(employment_records.offer_date,employment_records.employment_open_date)).label("avg_time"))
            .filter(employment_records.employment_open_date.isnot(None)).group_by(employment_records.class_no_snapshot).all())
    dict_list=[{
        "class_no_snapshot": e.class_no_snapshot,
        "avg_time":e.avg_time,
    } for e in emps]
    if not dict_list:
        raise HTTPException(404,detail="找不到数据")
    return {
        "code": 200,
        "data": dict_list,
    }

