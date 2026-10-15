# -*- coding: utf-8 -*-
"""
老师数据模型（ORM 模型）
========================
对应数据库表 teachers。
字段严格按《基础版数据库设计文档 V1.1》定义。
"""
from datetime import datetime

# Column：定义数据库列；DateTime时间；Enum枚举；Index索引；Numeric小数；String字符串
from sqlalchemy import BigInteger, Column, DateTime, Enum, Index, Integer, Numeric, String
# TINYINT MySQL特有的短整型，用于存0/1逻辑删除标记
from sqlalchemy.dialects.mysql import TINYINT

# [修改说明] 原代码：database.Base 和旧 app.core.database.Base 两种导入都被注释；修改原因：定义 Teacher 类时 Base 未定义，任何老师路由导入都会在启动阶段 NameError；修改为：从小组统一的 database.py 导入 Base。
from database import Base


class Teacher(Base):
    """老师表"""
    # 指定映射的mysql真实表名
    __tablename__ = "teachers"
    # 表额外配置：创建索引、数据库引擎、字符集、注释
    __table_args__ = (
        # 创建联合索引：name + is_deleted，提高按姓名查询的速度
        Index("idx_teachers_name_deleted", "name", "is_deleted"),
        {"comment": "老师表", "mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    # [修改说明] 原代码：主键直接使用 BigInteger；修改原因：MySQL 目标库保持 BIGINT 没问题，但 SQLite 集成测试只有 INTEGER PRIMARY KEY 才能自动生成主键；修改为：MySQL 仍使用 BigInteger，仅在 SQLite 方言下映射为 Integer，不改变生产表类型。
    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, comment="老师主键ID")
    # 业务老师编号，唯一不重复，不能为空
    teacher_no = Column(String(30), nullable=False, unique=True, comment="老师编号")
    # 老师姓名，非空
    name = Column(String(50), nullable=False, comment="老师姓名")
    # 性别枚举，只能存男/女/其他，可以为空；name指定mysql枚举类型名字
    gender = Column(Enum("男", "女", "其他", name="teacher_gender_enum"), nullable=True, comment="性别：男/女/其他")
    # 教学专长，specialty，可空
    specialty = Column(String(100), nullable=True, comment="教学专长")
    # 手机号，只存放电话号码
    phone = Column(String(30), nullable=True, comment="手机号（只保存电话）")
    # 补充联系方式，微信邮箱等
    contact_info = Column(String(150), nullable=True, comment="补充联系方式，如微信、邮箱")
    # Numeric(总位数,小数位数)；server_default数据库层面默认值；教学年限允许小数5.5年
    teaching_years = Column(Numeric(5, 2), nullable=False, default=0, server_default="0", comment="教学年限，可为小数")
    # 老师状态：在职、离职
    teacher_status = Column(String(20), nullable=False, default="在职", comment="老师状态：在职/离职")
    # [修改说明] 原代码：teachers 仅保存任职状态 teacher_status；修改原因：前端排班还需独立区分“可授课/暂停授课”，且暂停授课老师必须禁止新增排班；修改为：新增 teaching_status 字段并默认可授课，旧有任职状态逻辑保持不变。
    teaching_status = Column(String(20), nullable=False, default="可授课", server_default="可授课", comment="授课状态：可授课/暂停授课")

    # ========== 公共字段：逻辑删除 + 时间戳 ==========
    # [修改说明] 原代码：is_deleted 直接使用 MySQL 专属 TINYINT；修改原因：生产 MySQL 正常，但通用测试数据库无法编译该类型；修改为：MySQL 继续使用 TINYINT，仅在 SQLite 方言下映射为 Integer。
    is_deleted = Column(TINYINT().with_variant(Integer, "sqlite"), nullable=False, default=0, server_default="0", comment="逻辑删除：0=未删除，1=已删除")
    # deleted_at记录逻辑删除时间，未删除时为null
    deleted_at = Column(DateTime, nullable=True, comment="逻辑删除时间")
    # 创建时间，默认取当前时间
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    # 更新时间；onupdate=datetime_now，记录被修改时自动刷新时间
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
