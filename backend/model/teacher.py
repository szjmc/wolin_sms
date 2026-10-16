"""
老师表 teachers 的 ORM 模型
联系方式约定：phone 只保存电话号码；contact_info 保存微信、邮箱等补充联系方式。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, Numeric, String
from sqlalchemy.dialects.mysql import TINYINT

from database import Base


class Teacher(Base):
    """老师表"""

    __tablename__ = "teachers"

    # 主键：BIGINT 自增
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="老师主键ID")
    # 老师编号：业务编号，唯一
    teacher_no = Column(String(30), nullable=False, unique=True, comment="老师编号")
    # 老师姓名
    name = Column(String(50), nullable=False, comment="老师姓名")
    # 性别：男 / 女 / 其他，可为空
    gender = Column(Enum("男", "女", "其他", name="teacher_gender_enum"), nullable=True, comment="性别：男/女/其他")
    # 教学专长
    specialty = Column(String(100), nullable=True, comment="教学专长")
    # 手机号：只保存电话号码
    phone = Column(String(30), nullable=True, comment="手机号（只保存电话）")
    # 补充联系方式：微信、邮箱等，可为空
    contact_info = Column(String(150), nullable=True, comment="补充联系方式，如微信、邮箱")
    # 教学年限：允许小数（如 5.5 年），不得为负数（由 Pydantic 校验）
    teaching_years = Column(Numeric(5, 2), nullable=False, default=0, server_default="0", comment="教学年限，可为小数")
    # 老师状态：在职 / 离职
    teacher_status = Column(String(20), nullable=False, default="在职", server_default="在职", comment="老师状态：在职/离职")
    # 授课状态：可授课 / 暂停授课。暂停后不能被排入任何新班级。
    teaching_status = Column(String(20), nullable=False, default="可授课", server_default="可授课", comment="授课状态：可授课/暂停授课")

    # ========== 公共字段：逻辑删除 + 时间戳 ==========
    is_deleted = Column(TINYINT, nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
