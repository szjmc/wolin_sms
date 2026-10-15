"""成绩路由"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from scheme.score import (ScoreCreate, ScoreUpdate, ScoreRead, ScoreReadWithStudent)
from dao.score import ScoreDAO
from model.student import Student
from scheme.score import ScoreSearchResponse
from model.score import Score
router = APIRouter(tags=["成绩管理"])
# ============================================================
# 接口 1：新增成绩
# ============================================================
@router.post("/scores", response_model=ScoreRead, status_code=201)
def create_score(
        score_data: ScoreCreate,
        db: Session = Depends(get_db)
):
    student = db.query(Student).filter(
        Student.id == score_data.student_id,
        Student.is_deleted == 0
    ).first()
    if not student:
        raise HTTPException(404, "学生不存在")
    existing = ScoreDAO.get_by_student_exam(
        db,
        score_data.student_id,
        score_data.exam_no
    )
    if existing:
        raise HTTPException(409, f"该学生第 {score_data.exam_no} 次考核已有成绩")
    new_score = ScoreDAO.create(
        db=db,
        student_id=score_data.student_id,
        exam_no=score_data.exam_no,
        score=score_data.score
    )
    return new_score
# ============================================================
# 接口 2：查学生成绩列表
# ============================================================
@router.get("/students/{student_id}/scores", response_model=List[ScoreReadWithStudent])
def get_student_scores_by_student_id(
        student_id: int,
        exam_no: int = Query(None, ge=1, description="按考核序次筛选"),
        db: Session = Depends(get_db)
):
    """查学生成绩（可按考核序次筛选）"""
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.is_deleted == 0
    ).first()
    if not student:
        raise HTTPException(404, "学生不存在")

    # 步骤 2：查成绩
    scores = ScoreDAO.get_by_student(db, student_id, exam_no)

    # 步骤 3：组装返回（含学生信息）
    result = []
    for score in scores:
        result.append({
            "id": score.id,
            "student_id": score.student_id,
            "exam_no": score.exam_no,
            "score": score.score,
            "created_at": score.created_at,
            "updated_at": score.updated_at,
            "student_name": student.name,
            "class_id": student.class_id
        })
    return result
# # ============================================================
# # 接口 3：按学生+考试次数查单条
# # ============================================================
@router.get("/students/{student_id}/scores/{exam_no}", response_model=ScoreRead)
def get_score_by_student_exam(
        student_id: int,
        exam_no: int,
        db: Session = Depends(get_db)
):
    """按学生+考试次数查单条成绩（业务接口）"""
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.is_deleted == 0
    ).first()
    if not student:
        raise HTTPException(404, "学生不存在")
    score = ScoreDAO.get_by_student_exam(db, student_id, exam_no)
    if not score:
        raise HTTPException(404, f"第 {exam_no} 次成绩不存在")
    return score
# # ============================================================
# # 接口 4：按学生+考试次数改
# # ============================================================
@router.patch("/students/{student_id}/scores/{exam_no}", response_model=ScoreRead)
def update_score_by_student_exam(
        student_id: int,
        exam_no: int,
        score_data: ScoreUpdate,
        db: Session = Depends(get_db)
):
    """按学生+考试次数改（业务接口）"""
    db_score = ScoreDAO.get_by_student_exam(db, student_id, exam_no)
    if not db_score:
        raise HTTPException(404, f"第 {exam_no} 次成绩不存在")

    # 如果要改 exam_no，检查冲突
    if score_data.exam_no is not None and score_data.exam_no != exam_no:
        existing = ScoreDAO.get_by_student_exam(db, student_id, score_data.exam_no)
        if existing:
            raise HTTPException(409, f"第 {score_data.exam_no} 次考核已有成绩")

    return ScoreDAO.update(
        db=db,
        score_id=db_score.id,
        score=score_data.score,
        exam_no=score_data.exam_no
    )
# # ============================================================
# # 接口 5：按学生+考试次数删
# # ============================================================
@router.delete("/students/{student_id}/scores/{exam_no}", status_code=204)
def delete_score_by_student_exam(
        student_id: int,
        exam_no: int,
        db: Session = Depends(get_db)
):
    """按学生+考试次数删（业务接口）"""
    db_score = ScoreDAO.get_by_student_exam(db, student_id, exam_no)
    if not db_score:
        raise HTTPException(404, f"第 {exam_no} 次成绩不存在")

    if not ScoreDAO.delete(db, db_score.id):
        raise HTTPException(500, "删除失败")
    return
# # ============================================================
# # 接口 6：多条件查询接口
# # ============================================================


@router.get(
    path="/scores/search",
    response_model=ScoreSearchResponse,
    summary="多条件搜索成绩"
)
def search_scores(
        keyword: str = Query(None, description="搜姓名/学号"),
        class_id: int = Query(None, description="按班级筛选"),
        exam_no: int = Query(None, ge=1, description="按考试序次筛选"),
        level: str = Query(None, pattern="^(优秀|良好|及格|不及格)$", description="分数段"),
        sort_by: str = Query("default", pattern="^(default|score_asc|score_desc)$", description="排序"),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db)
):
    """多条件搜索成绩（5 个筛选条件）"""
    # 1. 基础查询
    query = db.query(Score).filter(Score.is_deleted == 0)
    # 2. 关键词（姓名/学号模糊搜索）
    if keyword:
        from sqlalchemy import or_
        from model.student import Student
        query = query.filter(
            or_(
                Score.student.has(Student.student_no.like(f"%{keyword}%")),
                Score.student.has(Student.name.like(f"%{keyword}%"))
            )
        )

    # 3. 班级
    if class_id:
        from model.student import Student
        query = query.filter(Score.student.has(Student.class_id == class_id))

    # 4. 考试序次
    if exam_no:
        query = query.filter(Score.exam_no == exam_no)

    # 5. 分数段（level 转分数范围）
    if level:
        score_ranges = {
            "优秀": (80, 100),
            "良好": (70, 80),
            "及格": (60, 70),
            "不及格": (0, 60),
        }
        min_s, max_s = score_ranges[level]
        query = query.filter(Score.score >= min_s, Score.score < max_s)

    # 6. 排序
    if sort_by == "score_asc":
        query = query.order_by(Score.score.asc())
    elif sort_by == "score_desc":
        query = query.order_by(Score.score.desc())
    else:
        query = query.order_by(Score.id.desc())

    # 7. 分页
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }