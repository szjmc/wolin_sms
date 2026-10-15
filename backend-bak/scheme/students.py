"""学生模块的 Pydantic 请求与响应模型。

年龄不接受客户端维护，始终由服务端依据出生日期动态计算。
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheme.common import Gender, check_not_null


# [修改说明] 原代码：StudentUpdate 的 gender 实际为必传字段，必填列可被 PATCH 成 null，响应使用 create_time/update_time 且缺少前端展示班级所需字段；修改原因：局部更新、统一响应和前端学生列表均无法按契约工作；修改为：保留 scheme/students.py 及原模型名，补齐枚举、非空保护、日期规则、动态年龄和班级展示字段。
class StudentCreate(BaseModel):
    """新增学生请求体。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    student_no: str = Field(
        min_length=1, max_length=30, description="学生编号，全局唯一，创建后不可修改"
    )
    class_id: int = Field(gt=0, description="所属培训班级 ID")
    name: str = Field(min_length=1, max_length=50, description="学生姓名")
    hometown: str | None = Field(default=None, max_length=100, description="籍贯")
    graduate_school: str | None = Field(
        default=None, max_length=150, description="原毕业院校"
    )
    major: str | None = Field(default=None, max_length=100, description="原专业")
    training_enrollment_date: date | None = Field(
        default=None, description="培训入学日期"
    )
    training_graduation_date: date | None = Field(
        default=None, description="培训毕业/结课日期"
    )
    education: str | None = Field(default=None, max_length=30, description="学历")
    consultant_no: str | None = Field(
        default=None, max_length=30, description="顾问编号"
    )
    birth_date: date = Field(description="出生日期，不能晚于今天")
    gender: Gender = Field(description="性别：男/女/其他")

    @model_validator(mode="after")
    def check_dates(self):
        if self.birth_date > date.today():
            raise ValueError("出生日期不能晚于今天")
        if (
            self.training_enrollment_date is not None
            and self.training_graduation_date is not None
            and self.training_graduation_date < self.training_enrollment_date
        ):
            raise ValueError("培训结课日期不能早于培训入学日期")
        return self


class StudentUpdate(BaseModel):
    """学生局部更新；学生编号创建后不可修改。"""

    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    class_id: int | None = Field(default=None, gt=0, description="所属培训班级 ID")
    name: str | None = Field(
        default=None, min_length=1, max_length=50, description="学生姓名"
    )
    hometown: str | None = Field(default=None, max_length=100, description="籍贯")
    graduate_school: str | None = Field(
        default=None, max_length=150, description="原毕业院校"
    )
    major: str | None = Field(default=None, max_length=100, description="原专业")
    training_enrollment_date: date | None = Field(
        default=None, description="培训入学日期；null 表示清空"
    )
    training_graduation_date: date | None = Field(
        default=None, description="培训毕业/结课日期；null 表示清空"
    )
    education: str | None = Field(default=None, max_length=30, description="学历")
    consultant_no: str | None = Field(
        default=None, max_length=30, description="顾问编号"
    )
    birth_date: date | None = Field(default=None, description="出生日期")
    gender: Gender | None = Field(default=None, description="性别：男/女/其他")

    @model_validator(mode="after")
    def check_fields(self):
        check_not_null(self, ["class_id", "name", "birth_date", "gender"])
        if self.birth_date is not None and self.birth_date > date.today():
            raise ValueError("出生日期不能晚于今天")
        # 培训日期需与数据库原值合并后判断，放在 API 层处理。
        return self


class StudentRead(BaseModel):
    """学生响应，包含动态年龄和所属班级展示信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    class_id: int
    class_no: str
    class_name: str | None
    name: str
    hometown: str | None
    graduate_school: str | None
    major: str | None
    training_enrollment_date: date | None
    training_graduation_date: date | None
    education: str | None
    consultant_no: str | None
    birth_date: date
    age: int
    gender: Gender
    # 当前小组后端尚无头像上传业务；返回 null 保持前端 DTO 兼容。
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime


class StudentPageResp(BaseModel):
    """兼容小组原导入名；新接口实际使用统一 ApiResponse[PageData] 包装。"""

    total: int
    page: int
    page_size: int
    items: list[StudentRead]
