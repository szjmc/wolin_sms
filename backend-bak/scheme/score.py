"""学生成绩模块的 Pydantic 模型。

核心查改删始终按「学生 ID + 考核序次」定位，不按成绩表自增 ID。
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# [修改说明] 原代码：ScoreUpdate 可为空且允许修改 exam_no，列表/搜索响应也没有统一 ApiResponse 契约所需的全员成绩字段；修改原因：空 PATCH 会静默成功，修改序次破坏业务定位，前端成绩大表无法展示学生和班级；修改为：PATCH 只接受必填 score，并补齐核心响应、全员大表和汇总模型。
class ScoreCreate(BaseModel):
    """新增成绩请求体。"""

    student_id: int = Field(gt=0, description="学生 ID")
    exam_no: int = Field(ge=1, description="考核序次，正整数")
    score: Decimal = Field(
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
        description="成绩，0~100，最多两位小数",
    )


class ScoreUpdate(BaseModel):
    """按学生和序次修改成绩；身份字段不允许通过请求体修改。"""

    score: Decimal = Field(
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
        description="新分数，0~100",
    )


class ScoreRead(BaseModel):
    """核心成绩响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    exam_no: int
    score: Decimal
    created_at: datetime
    updated_at: datetime


class ScoreOverview(ScoreRead):
    """全员成绩大表使用的学生、班级、成绩融合 DTO。"""

    student_no: str
    name: str
    class_id: int
    class_no: str
    class_name: str
    grade: str


class ScoreSummary(BaseModel):
    """当前筛选条件下的成绩汇总。"""

    total: int
    average_score: Decimal | None
    pass_count: int
    excellent_count: int


class ScoreImportResult(BaseModel):
    imported: int
    message: str


# 保留小组原模型名，避免尚未迁移的调用方导入失败。
class ScoreReadWithStudent(ScoreRead):
    student_name: str | None = None
    class_id: int | None = None


class ScoreListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ScoreRead]


class ScoreSearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ScoreReadWithStudent]
