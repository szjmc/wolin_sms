"""
接口层公共工具
==============
多个接口文件都会用到的小工具都放在这里：
1. ERROR_RESPONSES：统一错误响应说明（只用于 Swagger 文档展示）
2. success / page_data：组装统一的成功响应和分页数据
3. calculate_age：根据出生日期计算年龄
4. calculate_birth_date_cutoff：把"年龄大于 N 岁"换算成出生日期条件
5. round_2：保留两位小数
6. calculate_annualized_salary：把薪资换算成年薪等价值
7. to_student_read：把学生 ORM 对象转换成响应模型（顺便计算年龄）
"""
import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from model.student import Student
from scheme.common import ErrorResponse
from scheme.student import StudentRead

# 统一的错误响应说明：注册到每个路由上，Swagger 文档里就能看到出错时返回什么格式
ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "业务规则不满足（code=40001）"},
    404: {"model": ErrorResponse, "description": "记录不存在或已删除（code=40401）"},
    409: {"model": ErrorResponse, "description": "编号重复或存在关联数据（code=40901）"},
    422: {"model": ErrorResponse, "description": "请求参数校验失败（code=42201）"},
}


def success(data=None):
    """组装统一的成功响应：{"code": 0, "message": "success", "data": data}"""
    return {"code": 0, "message": "success", "data": data}


def page_data(items, total, page, page_size):
    """组装统一的分页数据：{"items": [...], "total": 总条数, "page": 页码, "page_size": 每页条数}"""
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def calculate_age(birth_date):
    """
    根据出生日期计算周岁年龄；出生日期为空时返回 None。
    算法：今年 - 出生年；如果今年的生日还没到，再减 1。
    """
    if birth_date is None:
        return None

    today = date.today()
    age = today.year - birth_date.year

    # 今年的生日还没到（月份没到，或者同一个月但日子没到），年龄减 1
    if today.month < birth_date.month:
        age = age - 1
    elif today.month == birth_date.month and today.day < birth_date.day:
        age = age - 1

    return age


def calculate_birth_date_cutoff(age_gt):
    """
    把"年龄大于 age_gt 岁"换算成"出生日期 <= 某一天"。

    推理过程：
        年龄 > age_gt
        等价于 年龄 >= age_gt + 1
        等价于 出生日期 <= 今天往前推 (age_gt + 1) 年的那一天

    这样查询时直接比较 birth_date 字段，不需要对每一行计算年龄，可以用上数据库索引。
    """
    today = date.today()
    target_year = today.year - (age_gt + 1)

    # 特殊情况：今天是 2 月 29 日，但目标年份不是闰年（没有 2 月 29 日），改用 2 月 28 日
    if today.month == 2 and today.day == 29 and not calendar.isleap(target_year):
        return date(target_year, 2, 28)

    return date(target_year, today.month, today.day)


def round_2(value):
    """保留两位小数（四舍五入），返回 Decimal；值为 None 时返回 None"""
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_annualized_salary(salary_amount, salary_period):
    """
    计算年薪等价值（只用于展示、排序和比较，不会修改原始薪资）：
    - MONTH（月薪）：月薪 × 12
    - YEAR（年薪）：年薪本身
    """
    if salary_amount is None:
        return None
    if salary_period == "MONTH":
        return round_2(salary_amount * 12)
    return round_2(salary_amount)


def to_student_read(student: Student) -> StudentRead:
    """
    把数据库中的学生对象转换成响应模型。
    数据库里没有 age 字段，这里根据出生日期实时计算年龄后再返回。
    """
    student_read = StudentRead.model_validate(student)
    student_read.age = calculate_age(student.birth_date)
    return student_read
