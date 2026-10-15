"""
数据库模型包
============

各业务模块从自己的模型文件导入 ORM 类；main.py 在注册对应路由时会先加载这些模型，
使 Base.metadata.create_all() 能看到已接入模块的数据表。
"""

# [修改说明] 原代码：从不存在的 app.core.database 导入 Base，并在包入口重复定义旧版 teacher 表；修改原因：导入任意 model 子模块时都会先执行本文件，原实现会直接 ModuleNotFoundError，且与 model/teacher.py 的 teachers 表重复映射；修改为：包入口不再定义 ORM 表，由各业务模型文件使用 database.Base 统一注册。
