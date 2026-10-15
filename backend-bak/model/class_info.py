# 说明：班级表的班主任、授课老师都关联这张表。

from sqlalchemy import Column, Integer, String, Date
from database import Base

# 班级实体模型，映射classes表
class ClassInfo(Base):
    __tablename__ = "classes"  # 小组统一的表名叫 classes

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    class_no = Column(String(50), unique=True, nullable=False, comment="班级编号（如 WL2024-A）")
    class_name = Column(String(50), nullable=False, comment="班级名称")
    start_date = Column(Date, comment="开课时间")
    completion_date = Column(Date, comment="结课时间")
    class_status = Column(String(20), comment="班级状态（如 在读、已结课）")

# 教师实体模型，映射teachers表
class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_no = Column(String(20), unique=True, nullable=False, comment="老师工号")
    name = Column(String(50), nullable=False, comment="老师姓名")
    specialty= Column(String(50), comment="授课科目")

# 班级-老师关联中间表
class ClassTeacherRelation(Base):
    __tablename__ = "class_teacher_relations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, nullable=False, comment="班级id（关联 classes.id）")
    teacher_id = Column(Integer, nullable=False, comment="老师id（关联 teachers.id）")
    relation_type = Column(String(20), comment="关系类型：班主任 / 授课老师")
    is_deleted = Column(Integer, default=0, comment="逻辑删除：0未删，1已删")

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    class_id = Column(Integer, comment="班级id（关联 classes.id）")
    name = Column(String(50), comment="学生姓名")

class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    student_id = Column(Integer, comment="学生id（关联 students.id）")
    exam_no = Column(Integer, comment="考试序次")
    score = Column(Integer, comment="考试成绩")
    is_deleted = Column(Integer, default=0, comment="逻辑删除：0未删，1已删")