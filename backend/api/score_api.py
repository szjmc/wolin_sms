"""
学生成绩接口
============
POST   /api/v1/scores                                      新增成绩
GET    /api/v1/students/{student_id}/scores                查询某个学生的成绩列表
GET    /api/v1/students/{student_id}/scores/{exam_no}      按学生 + 考核序次查一条成绩
PATCH  /api/v1/students/{student_id}/scores/{exam_no}      按学生 + 考核序次改分数
DELETE /api/v1/students/{student_id}/scores/{exam_no}      按学生 + 考核序次逻辑删除成绩

为什么不按成绩 id 查改删？
    老师手里只有「学生 + 第几次考试」，没有成绩表的自增主键。
    同一学生同一考核序次在未删除数据中最多只有一条，所以 (student_id, exam_no) 足以唯一定位。

规则：同一学生同一考核序次只允许一条「未删除」的成绩；成绩被逻辑删除后，可以重新录入该序次。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, get_current_user, get_current_user, page_data, success
from api.permissions import check_permission
from dao import score_dao, student_dao
from database import get_db
from scheme.common import ApiResponse, PageData
from model.user import User
from scheme.score import ScoreCreate, ScoreRead, ScoreUpdate

router = APIRouter(tags=["学生成绩"], responses=ERROR_RESPONSES, dependencies=[Depends(get_current_user)])


def get_visible_score_by_exam(db: Session, student_id: int, exam_no: int):
    """
    按「学生ID + 考核序次」查出一条可见成绩。
    可见 = 成绩未删除，并且所属学生也未删除。
    学生不存在、成绩不存在时都返回 404。
    """
    # 第 1 步：先确认学生本人还在（已删除学生的成绩对普通业务不可见）
    if student_dao.get_student_by_id(db, student_id) is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    # 第 2 步：用学生 + 考核序次定位成绩，不用成绩主键 id
    score = score_dao.get_active_score_by_exam(db, student_id, exam_no)
    if score is None:
        raise HTTPException(status_code=404, detail="该学生这一次考核的成绩不存在或已删除")
    return score


@router.post("/scores", response_model=ApiResponse[ScoreRead], status_code=201, summary="新增成绩")
def create_score(
    payload: ScoreCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """给学生录入一次考核成绩。同一学生同一序次已有有效成绩时返回 409。"""
    # 第 1 步：学生必须存在且未删除
    student = student_dao.get_student_by_id(db, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    # 第 1.5 步：权限校验——班主任/授课老师只能给自己班的学生录成绩
    check_permission(current, "score", student.class_id)

    # 第 2 步：同一学生同一考核序次只能有一条未删除的成绩
    if score_dao.get_active_score_by_exam(db, payload.student_id, payload.exam_no) is not None:
        raise HTTPException(status_code=409, detail="该学生这一次考核的成绩已存在，请按学生和考核序次修改")

    # 第 3 步：保存到数据库
    score = score_dao.create_score(db, payload.model_dump())
    return success(ScoreRead.model_validate(score))


@router.get(
    "/students/{student_id}/scores",
    response_model=ApiResponse[PageData[ScoreRead]],
    summary="查询学生成绩列表（只返回有效成绩）",
)
def list_student_scores(
    student_id: int,
    exam_no: int | None = Query(default=None, ge=1, description="考核序次，不传则返回该学生全部有效成绩"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，默认 20，最大 100"),
    db: Session = Depends(get_db),
):
    """列出某个学生的有效成绩。已删除学生返回 404。"""
    # 学生必须存在且未删除（已删除学生的成绩在普通查询中不展示）
    if student_dao.get_student_by_id(db, student_id) is None:
        raise HTTPException(status_code=404, detail="学生不存在或已删除")

    scores, total = score_dao.list_scores_by_student(db, student_id, page, page_size, exam_no=exam_no)

    items = []
    for score in scores:
        items.append(ScoreRead.model_validate(score))
    return success(page_data(items, total, page, page_size))


@router.get(
    "/students/{student_id}/scores/{exam_no}",
    response_model=ApiResponse[ScoreRead],
    summary="按学生 + 考核序次查询一条成绩",
)
def get_score_by_exam(student_id: int, exam_no: int, db: Session = Depends(get_db)):
    """业务查单条：用学生编号对应的 id 和第几次考试定位成绩，不按成绩主键 id 查找。"""
    score = get_visible_score_by_exam(db, student_id, exam_no)
    return success(ScoreRead.model_validate(score))


@router.patch(
    "/students/{student_id}/scores/{exam_no}",
    response_model=ApiResponse[ScoreRead],
    summary="按学生 + 考核序次修改分数",
)
def update_score_by_exam(
    student_id: int,
    exam_no: int,
    payload: ScoreUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    业务改：老师改的是「某学生第几次考试的分数」。
    路径里的 exam_no 就是身份，请求体只传新的 score。
    """
    score = get_visible_score_by_exam(db, student_id, exam_no)
    # 权限校验：只能改自己班学生的成绩
    check_permission(current, "score", student_dao.get_student_by_id(db, student_id).class_id)

    # 只改分数，不改考核序次、不改所属学生
    score = score_dao.update_score(db, score, {"score": payload.score})
    return success(ScoreRead.model_validate(score))


@router.delete(
    "/students/{student_id}/scores/{exam_no}",
    status_code=204,
    summary="按学生 + 考核序次逻辑删除成绩",
)
def delete_score_by_exam(
    student_id: int,
    exam_no: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    业务删：按学生 + 考核序次打删除标记。
    删除后同一序次可以重新录入（因为普通查询只看 is_deleted=0 的记录）。
    """
    score = get_visible_score_by_exam(db, student_id, exam_no)
    # 权限校验：只能删自己班学生的成绩
    check_permission(current, "score", student_dao.get_student_by_id(db, student_id).class_id)
    score_dao.delete_score(db, score)
    return Response(status_code=204)
