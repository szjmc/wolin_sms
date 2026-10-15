from datetime import datetime,timezone
from sqlalchemy import Column, BigInteger, Integer, DECIMAL,DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from database import Base



class Score(Base):
    __tablename__ = "scores"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    student_id = Column(BigInteger,ForeignKey("students.id", ondelete="RESTRICT"),nullable=False,comment="学生 ID")
    exam_no = Column(Integer, nullable=False, comment="考核序次")
    score = Column(DECIMAL(5, 2), nullable=False, comment="分数 0-100")
    is_deleted = Column(Integer, nullable=False, default=0, comment="逻辑删除")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), comment="创建时间")
    updated_at = Column(DateTime,nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc),comment="更新时间")
    student = relationship("Student", back_populates="scores", lazy="joined")

    def __repr__(self):
        return f"<Score id={self.id} student={self.student_id} exam={self.exam_no} score={self.score}>"


