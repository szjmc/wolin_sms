"""考核成绩表 ORM 模型。

同一学生同一考核序次只允许一条有效成绩；因逻辑删除后允许重录，不建立普通
``UNIQUE(student_id, exam_no)``，由业务层仅检查 ``is_deleted = 0`` 的记录。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, Numeric
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


# [修改说明] 原代码：Score 使用无法在 SQLite 自增的 BigInteger 主键、带时区时间，并声明了指向不存在 Student.scores 的 back_populates；修改原因：启用路由后会出现主键不自增或 ORM 映射初始化失败；修改为：保留 model/score.py 与字段结构，补充测试方言变体、统一审计字段并移除未被业务使用的双向关系。
class Score(Base):
    """学生一次考核的成绩记录。"""

    __tablename__ = "scores"
    __table_args__ = (
        Index(
            "idx_scores_student_deleted_exam",
            "student_id",
            "is_deleted",
            "exam_no",
        ),
        {"comment": "考核成绩表", "mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="成绩主键ID",
    )
    student_id = Column(
        BigInteger,
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        comment="学生ID",
    )
    exam_no = Column(Integer, nullable=False, comment="考核序次，从 1 开始")
    score = Column(Numeric(5, 2), nullable=False, comment="成绩，0~100")

    is_deleted = Column(
        TINYINT().with_variant(Integer, "sqlite"),
        nullable=False,
        default=0,
        server_default="0",
        comment="逻辑删除：0=未删除，1=已删除",
    )
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    def __repr__(self):
        return (
            f"<Score id={self.id} student={self.student_id} "
            f"exam={self.exam_no} score={self.score}>"
        )
