from datetime import datetime

from sqlalchemy import (Column, Integer, String, Date, Boolean, DateTime)

from database import Base


class StudentDB(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(64), unique=True, nullable=False, index=True, comment="学生编号")
    class_id = Column(Integer, nullable=True, comment="班级")
    name = Column(String(32), nullable=False, comment="姓名")
    hometown = Column(String(128), nullable=True, comment="籍贯")
    graduate_school = Column(String(128), nullable=True, comment="毕业院校")
    major = Column(String(128), nullable=True, comment="专业")
    training_enrollment_date = Column(Date, nullable=True, comment="入学日期")
    training_graduation_date = Column(Date, nullable=True, comment="毕业日期")
    education = Column(String(64), nullable=True, comment="学历")
    birth_date = Column(Date, nullable=True, comment="出生日期")
    gender = Column(String(8), nullable=True, comment="性别 女/男/其他")
    consultant_no = Column(String(64), nullable=True, comment="顾问编号 预留扩展，无外键")
    is_deleted = Column(Boolean, default=False, index=True, comment="逻辑删除标记")
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


