"""
学生成绩模块的 Pydantic 模型
============================
业务约定：查、改、删成绩一律按「学生ID + 考核序次」定位，
不使用成绩表的自增主键 id。因为老师改成绩时手里只有「张三第 2 次考核」，没有成绩 id。
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ScoreCreate(BaseModel):
    """新增成绩请求体。同一学生同一考核序次只允许一条未删除的成绩。"""

    student_id: int = Field(gt=0, description="学生ID（必须是未删除的学生）", examples=[1])
    exam_no: int = Field(ge=1, description="考核序次，正整数，1 表示第 1 次考核", examples=[1])
    score: Decimal = Field(
        ge=0, le=100, max_digits=5, decimal_places=2,
        description="成绩，范围 0~100，最多两位小数", examples=[88.5],
    )


class ScoreUpdate(BaseModel):
    """
    按「学生 + 考核序次」修改成绩时的请求体。
    考核序次已经在 URL 路径里，这里只允许改分数。
    """

    score: Decimal = Field(
        ge=0, le=100, max_digits=5, decimal_places=2,
        description="成绩，范围 0~100", examples=[92],
    )


class ScoreRead(BaseModel):
    """成绩响应数据"""

    # from_attributes=True：允许直接从 SQLAlchemy ORM 对象创建这个模型
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    exam_no: int
    score: Decimal
    created_at: datetime
    updated_at: datetime
