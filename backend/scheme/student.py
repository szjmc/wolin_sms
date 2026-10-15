"""
学生模块的 Pydantic 模型

注意：
1. 请求体里没有 age 字段——年龄不接受客户端提交，由服务端根据出生日期计算。
2. training_enrollment_date / training_graduation_date 是"培训机构"的入学、结课日期，
   不是原毕业院校的日期。
3. 必填和选填的分界：
   - 新增时必填：student_no、class_id、name、birth_date、gender（数据库 NOT NULL）
   - 可选：hometown、graduate_school、major、education、consultant_no、两个培训日期
     （学生可以先建档再慢慢补全，所以允许为空）
   - PATCH 时所有字段都不必传，但必填字段一旦传了就不能传 null（见 check_not_null）
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import Gender, check_not_null


class StudentCreate(BaseModel):
    """新增学生请求体"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    student_no: str = Field(min_length=1, max_length=30, description="学生编号，全局唯一，创建后不可修改", examples=["ST20260001"])
    class_id: int = Field(gt=0, description="所属培训班级ID（必须是未删除的班级）", examples=[1])
    name: str = Field(min_length=1, max_length=50, description="学生姓名", examples=["张三"])
    hometown: str | None = Field(default=None, max_length=100, description="籍贯", examples=["江苏南京"])
    graduate_school: str | None = Field(default=None, max_length=150, description="原毕业院校（不是培训机构）", examples=["南京某大学"])
    major: str | None = Field(default=None, max_length=100, description="原专业", examples=["计算机科学与技术"])
    training_enrollment_date: date | None = Field(default=None, description="培训入学日期（培训机构的入学时间）", examples=["2026-03-01"])
    training_graduation_date: date | None = Field(default=None, description="培训毕业/结课日期（培训机构的结课时间）")
    education: str | None = Field(default=None, max_length=30, description="学历", examples=["本科"])
    consultant_no: str | None = Field(default=None, max_length=30, description="顾问编号（扩展预留字段）", examples=["C001"])
    birth_date: date = Field(description="出生日期，不能晚于今天；年龄由服务端自动计算", examples=["2004-05-18"])
    gender: Gender = Field(description="性别：男/女/其他", examples=["男"])

    @model_validator(mode="after")
    def check_dates(self):
        # 规则 1：出生日期不能晚于今天
        if self.birth_date > date.today():
            raise ValueError("出生日期不能晚于今天")
        # 规则 2：两个培训日期都填写时，培训结课日期不能早于培训入学日期
        if self.training_enrollment_date is not None and self.training_graduation_date is not None:
            if self.training_graduation_date < self.training_enrollment_date:
                raise ValueError("培训结课日期不能早于培训入学日期")
        return self


class StudentUpdate(BaseModel):
    """更新学生请求体（PATCH，学生编号不允许修改）"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    class_id: int | None = Field(default=None, gt=0, description="所属培训班级ID")
    name: str | None = Field(default=None, min_length=1, max_length=50, description="学生姓名")
    hometown: str | None = Field(default=None, max_length=100, description="籍贯")
    graduate_school: str | None = Field(default=None, max_length=150, description="原毕业院校")
    major: str | None = Field(default=None, max_length=100, description="原专业")
    training_enrollment_date: date | None = Field(default=None, description="培训入学日期")
    training_graduation_date: date | None = Field(default=None, description="培训毕业/结课日期")
    education: str | None = Field(default=None, max_length=30, description="学历")
    consultant_no: str | None = Field(default=None, max_length=30, description="顾问编号")
    birth_date: date | None = Field(default=None, description="出生日期，不能晚于今天")
    gender: Gender | None = Field(default=None, description="性别：男/女/其他")

    @model_validator(mode="after")
    def check_fields(self):
        # 数据库必填字段：PATCH 时可以不传，但不能传 null
        check_not_null(self, ["class_id", "name", "birth_date", "gender"])
        # 出生日期不能晚于今天
        if self.birth_date is not None and self.birth_date > date.today():
            raise ValueError("出生日期不能晚于今天")
        # 培训日期的先后顺序需要结合数据库中的原值判断，放在接口层检查
        return self


class StudentRead(BaseModel):
    """
    学生响应数据。
    注意：student_no、name、birth_date、gender、age 都是必填（没有 | None），
    因为数据库里这几个字段都是 NOT NULL，前端可以放心直接展示，不用判空。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    class_id: int
    name: str
    hometown: str | None
    graduate_school: str | None
    major: str | None
    training_enrollment_date: date | None
    training_graduation_date: date | None
    education: str | None
    consultant_no: str | None
    birth_date: date
    age: int = Field(description="年龄：服务端根据出生日期实时计算，数据库不保存；出生日期必填所以年龄一定有值")
    gender: Gender
    created_at: datetime
    updated_at: datetime
