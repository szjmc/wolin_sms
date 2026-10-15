"""
班级管理路由
============
POST   /api/v1/classes             新增班级
GET    /api/v1/classes             班级分页列表
GET    /api/v1/classes/{class_id}  班级详情
PATCH  /api/v1/classes/{class_id}  局部更新班级
DELETE /api/v1/classes/{class_id}  逻辑删除班级
"""
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from api.common import ERROR_RESPONSES, page_data, round_2, success
from dao import class_info_dao, class_teacher_dao
from dao import statistics as statistics_dao
from dao import teacher as teacher_dao
from database import get_db
from scheme.class_info import ClassCreate, ClassRead, ClassUpdate
from scheme.common import ApiResponse, ClassStatus, PageData
from scheme.statistics import ClassOverview

# [修改说明] 原代码：接口按 class_no 查改删、使用 PUT 和 code=200 裸响应，删除时由 DAO 物理删除班级及关系；修改原因：与前端数字 ID、PATCH、统一响应和历史保留契约不一致；修改为：保留小组 APIRouter(prefix="/classes") 结构，五个核心接口改为按 class_id 操作、统一响应模型和逻辑删除。
router = APIRouter(prefix="/classes", tags=["班级管理"], responses=ERROR_RESPONSES)


def _to_class_read(db: Session, class_info) -> ClassRead:
    """聚合班级基础信息、学生数和当前教学团队。"""
    base = ClassRead.model_validate(class_info).model_dump()
    head_teacher = None
    lecturers = []
    for relation, related_teacher in class_teacher_dao.list_class_teacher_rows(
        db, class_info.id
    ):
        if relation.relation_type == "班主任":
            head_teacher = related_teacher
        elif relation.relation_type == "授课老师":
            lecturers.append(related_teacher)
    return ClassRead.model_validate(
        {
            **base,
            "total_students": class_info_dao.count_students_by_class(
                db, class_info.id
            ),
            "head_teacher": head_teacher,
            "teachers": lecturers,
        }
    )


def _get_assignable_teacher(db: Session, teacher_id: int):
    """校验初始排班老师存在、可授课且未被其它未结课班级占用。"""
    teacher = teacher_dao.get_teacher_by_id(db, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="老师不存在或已删除")
    if teacher.teacher_status != "在职" or teacher.teaching_status != "可授课":
        raise HTTPException(
            status_code=409,
            detail=f"{teacher.name} 当前不可安排授课",
        )
    if class_teacher_dao.get_teacher_busy_relation(db, teacher_id) is not None:
        raise HTTPException(
            status_code=409,
            detail="老师已负责未结课班级，一个老师同一时间只能负责一个班级",
        )
    return teacher


@router.post("", response_model=ApiResponse[ClassRead], status_code=201, summary="新增班级")
def create_class(payload: ClassCreate, db: Session = Depends(get_db)):
    # 班号对包括已逻辑删除记录在内的整张表保持唯一。
    if class_info_dao.get_class_by_no(db, payload.class_no) is not None:
        raise HTTPException(status_code=409, detail="班级编号已存在")

    # [修改说明] 原代码：建班只写 classes 表；修改原因：前端会同时提交 head_teacher_id 和 teacher_ids，必须在写入前执行完整排班校验并保证原子性；修改为：先校验全部老师和三条规则，再由 DAO 在一个事务中创建班级及关系。
    lecturer_ids = [*payload.teacher_ids]
    if payload.teacher_id is not None:
        lecturer_ids.append(payload.teacher_id)
    has_assignments = payload.head_teacher_id is not None or bool(lecturer_ids)
    if payload.class_status == "已结课" and has_assignments:
        raise HTTPException(status_code=409, detail="已结课班级不能新增排班")

    teacher_ids = [
        *([payload.head_teacher_id] if payload.head_teacher_id is not None else []),
        *lecturer_ids,
    ]
    for teacher_id in teacher_ids:
        _get_assignable_teacher(db, teacher_id)

    relations = []
    if payload.head_teacher_id is not None:
        relations.append(
            {"teacher_id": payload.head_teacher_id, "relation_type": "班主任"}
        )
    relations.extend(
        {"teacher_id": teacher_id, "relation_type": "授课老师"}
        for teacher_id in lecturer_ids
    )
    class_data = payload.model_dump(
        exclude={"head_teacher_id", "teacher_ids", "teacher_id"}
    )
    class_info = class_info_dao.create_class_with_relations(
        db, class_data, relations
    )
    return success(_to_class_read(db, class_info))


@router.get("", response_model=ApiResponse[PageData[ClassRead]], summary="班级分页列表")
def list_classes(
    class_no: str | None = Query(default=None, description="班级编号（精确匹配）"),
    class_name: str | None = Query(default=None, description="班级名称（模糊匹配）"),
    class_status: ClassStatus | None = Query(default=None, description="班级状态"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，最大 100"),
    db: Session = Depends(get_db),
):
    status_value = class_status.value if class_status is not None else None
    class_list, total = class_info_dao.list_classes(
        db,
        page,
        page_size,
        class_no=class_no,
        class_name=class_name,
        class_status=status_value,
    )
    # [修改说明] 原代码：列表只序列化 classes 表；修改原因：前端班级表直接展示学生数及教学团队；修改为：逐班聚合有效关系和学生总数后返回扩展 ClassRead。
    items = [_to_class_read(db, class_info) for class_info in class_list]
    return success(page_data(items, total, page, page_size))


# [修改说明] 原代码：班级详情只返回档案和教学团队；修改原因：前端班级概览页还需要性别分布、成绩覆盖/及格率/平均分、全达标人数和按历史快照统计的已就业人数；修改为：增加只读 overview 接口，全部聚合均复用统计 DAO 并排除逻辑删除数据。
@router.get(
    "/{class_id}/overview",
    response_model=ApiResponse[ClassOverview],
    summary="班级档案、学情及就业概览",
)
def get_class_overview(class_id: int, db: Session = Depends(get_db)):
    class_info = class_info_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    gender_counts = {"男": 0, "女": 0, "其他": 0}
    for row in statistics_dao.count_students_group_by_class_and_gender(
        db, class_id=class_id
    ):
        gender_counts[row.gender] = int(row.student_count)

    score_summary = statistics_dao.get_class_score_summary(db, class_id)
    total_scores = int(score_summary.total_scores or 0)
    passing_scores = int(score_summary.passing_scores or 0)
    pass_rate = None
    if total_scores:
        pass_rate = (
            Decimal(passing_scores) * Decimal("100") / Decimal(total_scores)
        ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    return success(
        ClassOverview(
            class_info=_to_class_read(db, class_info),
            total_students=sum(gender_counts.values()),
            male_count=gender_counts["男"],
            female_count=gender_counts["女"],
            other_count=gender_counts["其他"],
            graded_students=int(score_summary.graded_students or 0),
            total_scores=total_scores,
            passing_scores=passing_scores,
            pass_rate=pass_rate,
            average_score=round_2(score_summary.average_score),
            qualified_students=statistics_dao.count_class_qualified_students(
                db, class_id
            ),
            employed_students=(
                statistics_dao.count_employed_students_by_class_snapshot(
                    db, class_info.class_no
                )
            ),
        )
    )


@router.get("/{class_id}", response_model=ApiResponse[ClassRead], summary="班级详情")
def get_class(class_id: int, db: Session = Depends(get_db)):
    class_info = class_info_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")
    return success(_to_class_read(db, class_info))


@router.patch("/{class_id}", response_model=ApiResponse[ClassRead], summary="更新班级（只传需要修改的字段）")
def update_class(class_id: int, payload: ClassUpdate, db: Session = Depends(get_db)):
    class_info = class_info_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    changes = payload.model_dump(exclude_unset=True)
    new_start_date = changes.get("start_date", class_info.start_date)
    new_completion_date = changes.get("completion_date", class_info.completion_date)
    if new_completion_date is not None and new_completion_date < new_start_date:
        raise HTTPException(status_code=400, detail="班级结课日期不能早于开班日期")

    # [修改说明] 原代码：已结课班级可直接改回未开班/在读；修改原因：其历史有效关系在结课期间不占用老师，老师可能已被安排到其它未结课班级，直接重开会破坏“一师一班”；修改为：状态重开前逐个校验关联老师仍在职、可授课且未被其它未结课班级占用。
    new_status = changes.get("class_status", class_info.class_status)
    if class_info.class_status == "已结课" and new_status != "已结课":
        for _relation, related_teacher in class_teacher_dao.list_class_teacher_rows(
            db, class_id
        ):
            if (
                related_teacher.teacher_status != "在职"
                or related_teacher.teaching_status != "可授课"
            ):
                raise HTTPException(
                    status_code=409,
                    detail="该班级有老师当前不可授课，请先解除关系后再重新开班",
                )
            if (
                class_teacher_dao.get_teacher_busy_relation(
                    db, related_teacher.id, exclude_class_id=class_id
                )
                is not None
            ):
                raise HTTPException(
                    status_code=409,
                    detail="该班级有老师已在其他未结课班级任职，请先解除后再重新开班",
                )

    class_info = class_info_dao.update_class(db, class_info, changes)
    return success(_to_class_read(db, class_info))


@router.delete("/{class_id}", status_code=204, summary="逻辑删除班级")
def delete_class(class_id: int, db: Session = Depends(get_db)):
    class_info = class_info_dao.get_class_by_id(db, class_id)
    if class_info is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")

    if class_info_dao.count_students_by_class(db, class_id) > 0:
        raise HTTPException(status_code=409, detail="该班级下仍有学生，不能删除")
    if class_info_dao.count_relations_by_class(db, class_id) > 0:
        raise HTTPException(status_code=409, detail="该班级还关联着老师，请先解除班级老师关系")

    class_info_dao.delete_class(db, class_info)
    return Response(status_code=204)


# [修改说明] 原代码：保留了按班号查询及格率的预留接口，但返回 code=200 且数据位于非统一结构；修改原因：该接口虽不属于 backend 的五个班级核心接口，但属于小组已有扩展，不应直接删除；修改为：继续保留原路径，并统一为 code=0/message/data 响应，成绩模块未接入时返回零成绩统计。
@router.get("/{class_no}/statistics", response_model=ApiResponse[dict], summary="查询班级统计（小组预留接口）")
def get_class_statistics(class_no: str, db: Session = Depends(get_db)):
    data = class_info_dao.get_class_statistics(db, class_no)
    if data is None:
        raise HTTPException(status_code=404, detail="班级不存在或已删除")
    return success(data)
