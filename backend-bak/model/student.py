"""
学生表 students 的 ORM 模型

重要约定：
1. 数据库只保存出生日期 birth_date，不保存 age 字段；年龄在接口返回时动态计算。
2. training_enrollment_date / training_graduation_date 是"培训机构"的入学、结课日期，
   不是学生原毕业院校的入学、毕业日期。原学历信息看 graduate_school 和 major。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class Student(Base):
    """学生表"""

    __tablename__ = "students"

    # 主键：BIGINT 自增
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="学生主键ID")
    # 学生编号：业务编号，唯一，创建后不允许修改
    student_no = Column(String(30), nullable=False, unique=True, comment="学生编号")
    # 所属培训班级ID：外键关联 classes.id
    class_id = Column(BigInteger, ForeignKey("classes.id"), nullable=False, comment="所属培训班级ID")
    # 学生姓名
    name = Column(String(50), nullable=False, comment="学生姓名")
    # 籍贯
    hometown = Column(String(100), nullable=True, comment="籍贯")
    # 原毕业院校（不是培训机构）
    graduate_school = Column(String(150), nullable=True, comment="原毕业院校")
    # 原专业
    major = Column(String(100), nullable=True, comment="原专业")
    # 培训入学日期（培训机构的时间）
    training_enrollment_date = Column(Date, nullable=True, comment="培训入学日期（培训机构）")
    # 培训毕业/结课日期（培训机构的时间）
    training_graduation_date = Column(Date, nullable=True, comment="培训毕业/结课日期（培训机构）")
    # 学历，如 本科 / 大专
    education = Column(String(30), nullable=True, comment="学历")
    # 顾问编号：扩展版的预留字段，暂时不建立外键
    consultant_no = Column(String(30), nullable=True, comment="顾问编号（扩展预留，不建外键）")
    # 出生日期：年龄由它动态计算
    birth_date = Column(Date, nullable=False, comment="出生日期（年龄由此动态计算）")
    # 性别：男 / 女 / 其他
    gender = Column(Enum("男", "女", "其他", name="student_gender_enum"), nullable=False, comment="性别：男/女/其他")

    # ========== 公共字段：逻辑删除 + 时间戳 ==========
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
