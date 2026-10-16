"""
班级模块的 Pydantic 模型
- ClassCreate：新增班级的请求体
- ClassUpdate：更新班级的请求体（PATCH，只传需要修改的字段；班级编号不允许修改）
- ClassRead：班级的响应数据
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import ClassStatus, check_not_null


class ClassCreate(BaseModel):
    """新增班级请求体"""

    # use_enum_values=True：枚举字段取出来直接是字符串（如 "在读"），方便存入数据库
    # str_strip_whitespace=True：自动去掉字符串首尾的空格
    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    class_no: str = Field(min_length=1, max_length=30, description="班级编号，全局唯一，创建后不可修改", examples=["WL2026-A"])
    class_name: str = Field(min_length=1, max_length=100, description="班级名称", examples=["Python 全栈开发 2026 春季班"])
    start_date: date = Field(description="开班日期", examples=["2026-03-01"])
    completion_date: date | None = Field(default=None, description="班级结课日期，未结课可不填", examples=["2026-09-30"])
    class_status: ClassStatus = Field(default="在读", description="班级状态：未开班/在读/已结课")

    @model_validator(mode="after")
    def check_dates(self):
        # 结课日期如果填写了，就不能早于开班日期
        if self.completion_date is not None and self.completion_date < self.start_date:
            raise ValueError("班级结课日期不能早于开班日期")
        return self


class ClassUpdate(BaseModel):
    """更新班级请求体（PATCH）"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    class_name: str | None = Field(default=None, min_length=1, max_length=100, description="班级名称")
    start_date: date | None = Field(default=None, description="开班日期")
    completion_date: date | None = Field(default=None, description="班级结课日期；显式传 null 表示清空")
    class_status: ClassStatus | None = Field(default=None, description="班级状态：未开班/在读/已结课")

    @model_validator(mode="after")
    def check_required_fields(self):
        # 这几个字段在数据库中是必填的：PATCH 时可以不传，但不能传 null
        check_not_null(self, ["class_name", "start_date", "class_status"])
        return self


class ClassRead(BaseModel):
    """班级响应数据"""

    # from_attributes=True：允许直接从 SQLAlchemy ORM 对象创建这个模型
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_no: str
    class_name: str
    start_date: date
    completion_date: date | None
    class_status: str
    created_at: datetime
    updated_at: datetime
