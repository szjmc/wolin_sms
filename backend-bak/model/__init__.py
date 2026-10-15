# -*- coding: utf-8 -*-
"""
老师数据模型（ORM 模型）
=======================
对应数据库表 teacher。
一个类就是一张表，一个属性就是一列。
"""
from sqlalchemy import Column, String

from app.core.database import Base


class Teacher(Base):
    __tablename__ = "teacher"  # 数据库表名

    # 老师编号，主键，字符串类型，最长 20 个字符
    teacher_id = Column(String(20), primary_key=True, comment="老师编号")

    # 老师姓名，非空
    name = Column(String(50), nullable=False, comment="老师姓名")

    # 性别，可空
    gender = Column(String(4), comment="性别")

    # 联系电话，可空
    phone = Column(String(20), comment="联系电话")

    # 教授科目，可空
    subject = Column(String(50), comment="教授科目/方向")

    # 职称，可空
    title = Column(String(50), comment="职称，如讲师、高级讲师")