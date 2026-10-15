"""学生 ORM 的兼容导入入口。

小组后续成绩、就业模块仍从 ``model.student`` 导入 ``Student``；正式定义统一放在
原学生模块使用的 ``model.students_model``，避免同一张 students 表重复映射。
"""

# [修改说明] 原代码：本文件再次定义完整 Student ORM，而学生 API 使用 students_model.StudentDB；修改原因：两者同时加载时 SQLAlchemy 会报 students 表重复定义，且字段约束和时间字段不一致；修改为：保留本文件及 Student 名称，只转出统一的 Student 类，不改变后续模块的导入路径。
from model.students_model import Student

__all__ = ["Student"]
