from fastapi import APIRouter, Depends,HTTPException,Query
from sqlalchemy.orm import Session
from scheme.students import StudentCreate, StudentRead,StudentUpdate,Gender,StudentPageResp
from database import get_db
from dao import students_dao
from model.students_model import StudentDB

router = APIRouter()

@router.post("/student",response_model=StudentRead,summary="创建学生信息")
def create_student(data:StudentCreate,db:Session = Depends(get_db)):
    if students_dao.get_stu_no(db,data.student_no):
        raise HTTPException(status_code=400,detail="学生编号已存在")
    # data.model_dump() 是将 Pydantic 模型转换为字典，** 用于将字典中的
    # 键值对展开为关键字参数，再传给 SQLAlchemy 的 StudentDB 模型，从而创建学生数据库对象
    db_obj = StudentDB(**data.model_dump())
    try:
        db.add(db_obj)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500,detail="新增学生失败")

    return db_obj
#
@router.get("/student/list", response_model=StudentPageResp,summary="分页查询学生")
def student_list(page:int = Query(1,ge = 1),
                 page_size : int = Query(20 , ge=1 , le = 100),
                 student_no : str = Query(...),
                 name : str  = Query(...),
                 class_id : int  =Query(gt=0),
                 gender: Gender = Query(None),
                 db = Depends(get_db)):

    total, records = students_dao.select_stu_list(
        db=db,
        student_no=student_no,
        name=name,
        class_id=class_id,
        gender=gender.value if gender is not None else None,
        page=page,
        page_size=page_size
    )

    list_records = []

    for r in records:
        student_data = {
            column.name: getattr(r, column.name)
            for column in StudentDB.__table__.columns
        }

        student_data["age"] = students_dao.calc_age(r.birth_date)

        list_records.append(StudentRead(**student_data))

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": list_records
    }

@router.get("/student/{student_no}",response_model=StudentRead,summary="查询学生详情")
def student_detail(student_no: str,db = Depends(get_db)):
    stu = students_dao.get_stu_no(db,student_no)
    if not stu:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    data = stu.__dict__

    data["age"] = students_dao.calc_age(stu.birth_date)

    return data

@router.patch("/student/{student_no}",response_model=StudentRead,summary="更新学生信息")
def update_student(
    student_no: str,
    update_data: StudentUpdate,
    db: Session = Depends(get_db)
):
    stu = students_dao.get_stu_no(db,student_no)

    if not stu:
        raise HTTPException(
            status_code=404,
            detail="学生不存在或已删除"
        )

    update_dict = update_data.model_dump(
        exclude_unset=True,
        mode="python"
    )

    if "birth_date" in update_dict and update_dict["birth_date"] is None:
        raise HTTPException(
            status_code=400,
            detail="出生日期不能为空"
        )

    enrollment = update_dict.get(
        "training_enrollment_date",
        stu.training_enrollment_date
    )
    graduation = update_dict.get(
        "training_graduation_date",
        stu.training_graduation_date
    )

    if enrollment and graduation and graduation < enrollment:
        raise HTTPException(
            status_code=400,
            detail="培训结课日期不能早于培训入学日期"
        )

    if "gender" in update_dict and update_dict["gender"] is not None:
        update_dict["gender"] = update_dict["gender"].value

    try:
        stu = students_dao.get_stu_no(db, student_no)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="更新学生失败"
        )

    data = {
        column.name: getattr(stu, column.name)
        for column in StudentDB.__table__.columns
    }
    data["age"] = students_dao.calc_age(stu.birth_date)

    return data

@router.delete("/student/{student_no}",summary="删除学生信息")
def delete_student(student_no: str,db = Depends(get_db)):
    stu = students_dao.get_stu_no(db, student_no)
    if not stu:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    stu.is_deleted = 1

    try:
        db.commit()

    except Exception:
        raise HTTPException(status_code=500, detail="删除学生失败")

    return {"msg": "逻辑删除成功", "student_no": student_no}