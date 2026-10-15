# 沃林学生管理系统 · 小组后端整合版

本目录保留小组原有的文件命名和分层结构，并补齐为可独立运行的 FastAPI 后端。
业务契约与仓库 `docs/`、前端 `src/` 以及完整参考后端 `backend/` 对齐。

## 技术栈

- Python 3.10+
- FastAPI + Pydantic v2
- SQLAlchemy 2
- MySQL 8.0（正式环境）
- SQLite（仅用于轻量集成验证）

## 快速启动

```bash
cd backend-bak
python -m venv .venv
source .venv/bin/activate        # Windows：.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # 修改 WOLIN_DB_URL
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后可访问：

- Swagger：<http://127.0.0.1:8000/docs>
- ReDoc：<http://127.0.0.1:8000/redoc>
- 健康检查：`GET /api/v1/health`

前端需要使用本后端时，在前端运行环境配置：

```env
WOLIN_API_URL=http://127.0.0.1:8000
```

浏览器继续请求前端自己的 `/api/v1/*`，Next.js 代理会把请求转发给 FastAPI，
不需要在浏览器代码中写后端地址。当前 Next.js 工程的 `/api/health` 仍会初始化其
预览 PostgreSQL 连接，所以执行前端 `build/start` 时还需要提供 `DATABASE_URL`；
该变量和 FastAPI 使用的 MySQL `WOLIN_DB_URL` 是两套独立配置。

## 数据库初始化与升级

新数据库直接执行：

```text
docs/sql/init_mysql.sql
```

已有数据库必须先备份，再按需执行：

```text
docs/sql/migrations/20261016_add_teacher_teaching_status.sql
docs/sql/migrations/20261016_add_employment_history_snapshots.sql
```

`Base.metadata.create_all()` 只会创建不存在的表，不会给已有表补列，因此不能替代迁移脚本。

## 目录职责

```text
backend-bak/
├── api/       # 路由、业务规则、统一响应
├── dao/       # 数据访问、分页、联表与统计查询
├── model/     # SQLAlchemy ORM
├── scheme/    # Pydantic 请求/响应模型
├── database.py
├── main.py
└── requirements.txt
```

小组原文件名继续保留，例如：

- 学生：`students_model.py` / `students_dao.py` / `students_api.py`
- 就业：`stu_records_model.py` / `stu_records_dao.py` / `stu_records_api.py`
- 班级与关系模型：`model/class_info.py`

## 全局约定

- 成功响应：`{"code": 0, "message": "success", "data": ...}`
- 分页数据：`{"items": [], "total": 0, "page": 1, "page_size": 20}`
- 新增返回 201，逻辑删除返回 204。
- 错误业务码为 HTTP 状态码 × 100 + 1。
- 普通查询和统计默认排除逻辑删除记录。
- 成绩、过往经历和就业记录还必须确保所属学生未删除。
- PATCH 只更新请求中实际出现的字段，数据库必填字段不能显式传 `null`。
- 金额与成绩使用 `Decimal`，金额 JSON 保留字符串小数语义。
- 年龄、年薪等价值、毕业年限及统计聚合均动态计算，不保存重复派生值。

## 当前接口范围

已接入班级、老师、排班关系、学生、成绩、过往经历、就业记录、统计分析、
工作台总览和班级概览。所有业务接口统一位于 `/api/v1` 下。
