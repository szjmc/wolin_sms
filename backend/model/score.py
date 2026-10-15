"""
考核成绩表 scores 的 ORM 模型

唯一性说明：
同一学生、同一考核序次只允许有一条"未删除"的成绩。
这里不建普通的 UNIQUE(student_id, exam_no) 唯一索引，因为那样的话成绩被逻辑删除后就无法重新录入。
所以改为在接口层新增/修改成绩前先查询检查（见 api/score_api.py）。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class Score(Base):
    """考核成绩表"""

    __tablename__ = "scores"

    # 主键：BIGINT 自增
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="成绩主键ID")
    # 学生ID：外键关联 students.id
    student_id = Column(BigInteger, ForeignKey("students.id"), nullable=False, comment="学生ID")
    # 考核序次：正整数，1 表示第 1 次考核
    exam_no = Column(Integer, nullable=False, comment="考核序次，从 1 开始")
    # 成绩：0~100，最多两位小数
    score = Column(Numeric(5, 2), nullable=False, comment="成绩，0~100")

    # ========== 公共字段：逻辑删除 + 时间戳 ==========
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
