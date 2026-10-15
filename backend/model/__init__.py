"""
数据库模型层（SQLAlchemy ORM 模型）
==================================
一个类对应一张数据表，一个类属性对应表中的一个字段。

这里把所有模型统一导入一次，作用是：
main.py 执行 Base.metadata.create_all() 时，SQLAlchemy 能"看到"所有的表并自动创建。
以后新增模型文件，记得在这里加一行导入。
"""
from model.class_info import ClassInfo
from model.class_teacher_relation import ClassTeacherRelation
from model.employment_record import EmploymentRecord
from model.past_experience import StudentPastExperience
from model.score import Score
from model.student import Student
from model.teacher import Teacher

__all__ = [
    "ClassInfo",
    "ClassTeacherRelation",
    "EmploymentRecord",
    "StudentPastExperience",
    "Score",
    "Student",
    "Teacher",
]
