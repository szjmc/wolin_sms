# [修改说明] 原代码：backend-bak/model/__init__.py 定义了过时的 Teacher 模型且未导入 User；
# 修改原因：对齐 backend/ 入口，create_all 需要看到 User 模型才能创建 users 表；
# 修改为：仅导入 User，避免与 backend-bak 其他模型文件重复注册同名数据表。
from model.user import User

__all__ = ["User"]
