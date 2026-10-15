from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from typing import List
class ScoreCreate(BaseModel):
    """新增成绩请求体"""
    student_id: int = Field(..., gt=0, description="学生 ID")
    exam_no: int = Field(..., ge=1, description="考核序次（正整数）")
    score: Decimal = Field(..., ge=0, le=100, description="分数 0-100")
class ScoreUpdate(BaseModel):
    """修改成绩请求体（部分更新）"""
    score: Decimal | None = Field(None, ge=0, le=100, description="分数")
    exam_no: int | None = Field(None, ge=1, description="考核序次")
class ScoreRead(BaseModel):
    """成绩响应体"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    exam_no: int
    score: Decimal
    created_at: datetime
    updated_at: datetime
class ScoreReadWithStudent(ScoreRead):
    """成绩响应（含学生信息）"""
    student_name: str | None = None
    class_id: int | None = None
class ScoreListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ScoreRead]
class ScoreSearchResponse(BaseModel):
    total: int = Field(description="总条数")
    page: int = Field(description="当前页")
    page_size: int = Field( description="每页条数")
    items: List[ScoreReadWithStudent] = Field( description="数据列表")
    model_config = ConfigDict(from_attributes=True)

