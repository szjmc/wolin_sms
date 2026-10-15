from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator
from enum import Enum

class ORMReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# 性别枚举
class Gender(str, Enum):
    MALE = "男"
    FEMALE = "女"
    OTHER = "其他"

class StudentCreate(BaseModel):
    student_no: str = Field(min_length=1, max_length=30)
    class_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=50)
    hometown: str | None = Field(default=None, max_length=100)
    graduate_school: str | None = Field(default=None, max_length=150)
    major: str | None = Field(default=None, max_length=100)
    training_enrollment_date: date | None = None
    training_graduation_date: date | None = None
    education: str | None = Field(default=None, max_length=30)
    consultant_no: str | None = Field(default=None, max_length=30)
    birth_date: date
    gender: Gender

    @model_validator(mode="after")
    def validate_training_dates(self):
        if (self.training_enrollment_date and self.training_graduation_date
            and self.training_graduation_date < self.training_enrollment_date):
            raise ValueError("培训结课日期不能早于培训入学日期")
        if self.birth_date > date.today():
            raise ValueError("出生日期不能晚于今天")
        return self

class StudentUpdate(BaseModel):
    class_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, max_length=50)
    hometown: str | None = Field(default=None, max_length=100)
    graduate_school: str | None = Field(default=None, max_length=150)
    major: str | None = Field(default=None, max_length=100)
    training_enrollment_date: date | None = None
    training_graduation_date: date | None = None
    education: str | None = Field(default=None, max_length=30)
    consultant_no: str | None = Field(default=None, max_length=30)
    birth_date: date | None = None
    gender: Gender

class StudentRead(ORMReadModel):
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
    birth_date: date | None
    age: int
    gender: Gender
    create_time: datetime
    update_time: datetime

class StudentPageResp(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[StudentRead]
