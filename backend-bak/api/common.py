"""
接口层公共工具
==============

[补全说明] backend-bak 原缺少统一响应、分页、年龄和薪资计算工具，导致多个已有
路由无法导入。本文件使用小组现有 scheme.students 命名，并对齐 backend 的业务口径。
"""
import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from scheme.common import ErrorResponse

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "业务规则不满足（code=40001）"},
    404: {"model": ErrorResponse, "description": "记录不存在或已删除（code=40401）"},
    409: {"model": ErrorResponse, "description": "编号重复或存在关联数据（code=40901）"},
    422: {"model": ErrorResponse, "description": "请求参数校验失败（code=42201）"},
}


def success(data=None):
    """组装统一成功响应。"""
    return {"code": 0, "message": "success", "data": data}


def page_data(items, total, page, page_size):
    """组装统一分页数据。"""
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def calculate_age(birth_date):
    """按出生日期动态计算周岁。"""
    if birth_date is None:
        return None
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def calculate_birth_date_cutoff(age_gt):
    """将“年龄大于 N 岁”转换为可走出生日期索引的日期上限。"""
    today = date.today()
    target_year = today.year - (age_gt + 1)
    if today.month == 2 and today.day == 29 and not calendar.isleap(target_year):
        return date(target_year, 2, 28)
    return date(target_year, today.month, today.day)


def round_2(value):
    """按 ROUND_HALF_UP 规则保留两位小数。"""
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_annualized_salary(salary_amount, salary_period):
    """MONTH 按月薪乘 12 换算；YEAR 保持原金额。"""
    if salary_amount is None:
        return None
    if salary_period == "MONTH":
        return round_2(salary_amount * 12)
    return round_2(salary_amount)


# [修改说明] 原代码：to_student_read 只返回旧 create_time/update_time 字段，且没有班号、班名和前端 DTO 中的头像占位；修改原因：学生列表和详情无法直接展示所属班级，响应也与正式审计字段不一致；修改为：接受可选班级对象并组装统一 StudentRead，年龄仍实时计算，未接入头像业务时稳定返回 null。
def to_student_read(student, class_info=None):
    """将学生 ORM 与可选班级信息组装成统一响应。"""
    # 延迟导入，避免公共工具加载时强制初始化学生 ORM。
    from scheme.students import StudentRead

    data = {
        "id": student.id,
        "student_no": student.student_no,
        "class_id": student.class_id,
        "class_no": getattr(class_info, "class_no", ""),
        "class_name": getattr(class_info, "class_name", None),
        "name": student.name,
        "hometown": student.hometown,
        "graduate_school": student.graduate_school,
        "major": student.major,
        "training_enrollment_date": student.training_enrollment_date,
        "training_graduation_date": student.training_graduation_date,
        "education": student.education,
        "consultant_no": student.consultant_no,
        "birth_date": student.birth_date,
        "age": calculate_age(student.birth_date),
        "gender": student.gender,
        "avatar_url": getattr(student, "avatar_url", None),
        "created_at": getattr(
            student, "created_at", getattr(student, "create_time", None)
        ),
        "updated_at": getattr(
            student, "updated_at", getattr(student, "update_time", None)
        ),
    }
    return StudentRead.model_validate(data)
