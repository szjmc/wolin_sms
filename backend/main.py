"""
FastAPI 应用入口
================
启动方式（在 backend 目录下执行）：
    uvicorn main:app --reload --port 8000

启动后打开浏览器：
    Swagger 文档：http://127.0.0.1:8000/docs
    ReDoc 文档：  http://127.0.0.1:8000/redoc

本文件只做 5 件事：
1. 自动创建数据表
2. 创建 FastAPI 应用，配置接口文档信息
3. 配置跨域 CORS
4. 注册统一的异常处理（把各种错误转换成统一的错误响应格式）
5. 注册所有业务路由
"""
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

import model  # noqa: F401  导入全部 ORM 模型，create_all 才能创建所有表
from api import (
    class_api,
    class_teacher_api,
    employment_record_api,
    past_experience_api,
    score_api,
    statistics_api,
    student_api,
    teacher_api,
)
from database import Base, engine, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wolin")

# ======================================================================
# 第 1 步：自动创建数据表
# create_all 只创建"还不存在"的表；已存在的表不会被修改或删除，可以放心重复执行。
# 注意：修改已有表的字段时，create_all 不会自动改表结构，需要手动执行 ALTER TABLE。
# ======================================================================
Base.metadata.create_all(bind=engine)

# ======================================================================
# 第 2 步：创建 FastAPI 应用（这些信息会显示在 Swagger 文档页面上）
# ======================================================================
API_DESCRIPTION = """
沃林学生管理系统 · 基础版后端接口（契约版本 V1.3）

**统一响应格式**
- 成功：`{"code": 0, "message": "success", "data": ...}`
- 列表：`data` 为 `{"items": [], "total": 0, "page": 1, "page_size": 20}`
- 失败：`{"code": 40401, "message": "错误说明", "details": []}`

**错误码**：40001 业务规则不满足（400）｜40401 不存在或已删除（404）｜
40901 编号冲突或存在关联数据（409）｜42201 参数校验失败（422）｜50001 服务器内部错误（500）

**通用规则**
- 新增成功返回 201；更新（PATCH）只传需要修改的字段；删除为逻辑删除，成功返回 204（无响应体）
- 所有普通查询和统计默认排除已逻辑删除的数据
- 学生年龄由出生日期动态计算；薪资同时保存金额和周期（MONTH 月薪 / YEAR 年薪）
"""

TAGS_METADATA = [
    {"name": "班级管理", "description": "班级的新增、查询、更新、逻辑删除"},
    {"name": "老师管理", "description": "老师档案维护（手机号、补充联系方式、教学年限）"},
    {"name": "班级老师关系", "description": "维护班主任、授课老师与班级的关系（关系也是逻辑删除）"},
    {"name": "学生管理", "description": "学生档案维护；年龄根据出生日期动态计算"},
    {"name": "学生成绩", "description": "同一学生同一考核序次只允许一条有效成绩"},
    {"name": "学生过往经历", "description": "一名学生可有多条过往经历"},
    {"name": "就业记录", "description": "一名学生可有多条就业记录并保留历史；薪资区分月薪/年薪"},
    {"name": "统计分析", "description": "所有统计均排除逻辑删除的数据"},
    {"name": "系统", "description": "首页、健康检查"},
]

app = FastAPI(
    title="沃林学生管理系统 API",
    version="1.3.0",
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
)

# ======================================================================
# 第 3 步：配置跨域 CORS（允许前端页面从其他端口/域名调用接口）
# 开发阶段允许所有来源；正式上线时请改成前端的真实域名，例如 ["https://wolin.example.com"]
# ======================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================================
# 第 4 步：统一异常处理（异常处理函数按 FastAPI 官方写法使用 async def）
# ======================================================================
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    处理接口里 raise HTTPException(...) 抛出的错误。
    业务码规则：HTTP 状态码 × 100 + 1，例如 400 → 40001，404 → 40401，409 → 40901。
    """
    business_code = exc.status_code * 100 + 1
    content = {"code": business_code, "message": str(exc.detail), "details": []}
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理 Pydantic 参数校验失败（字段类型不对、超出范围、自定义校验不通过等），返回 422。
    """
    details = []
    for error in exc.errors():
        # error["loc"] 形如 ("body", "birth_date")，拼成 "body.birth_date" 方便前端定位字段
        field_parts = []
        for part in error["loc"]:
            field_parts.append(str(part))
        details.append({"field": ".".join(field_parts), "reason": error["msg"]})

    content = {"code": 42201, "message": "请求参数校验失败", "details": details}
    return JSONResponse(status_code=422, content=content)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    处理数据库约束冲突（例如并发请求同时插入了相同的编号），返回 409。
    正常情况下接口层会先检查，这里是最后一道保险。
    """
    logger.warning("数据库约束冲突：%s", exc)
    content = {"code": 40901, "message": "数据冲突：违反了数据库唯一约束或外键约束", "details": []}
    return JSONResponse(status_code=409, content=content)


@app.exception_handler(Exception)
async def unknown_exception_handler(request: Request, exc: Exception):
    """
    处理所有没有预料到的错误，返回 500。
    错误详情只记录到服务器日志里，不返回给客户端（避免泄露内部信息）。
    """
    logger.exception("服务器内部错误：%s", exc)
    content = {"code": 50001, "message": "服务器内部错误，请联系管理员", "details": []}
    return JSONResponse(status_code=500, content=content)


# ======================================================================
# 第 5 步：注册所有业务路由，统一加上 /api/v1 前缀
# ======================================================================
API_PREFIX = "/api/v1"

app.include_router(class_api.router, prefix=API_PREFIX)
app.include_router(teacher_api.router, prefix=API_PREFIX)
app.include_router(class_teacher_api.router, prefix=API_PREFIX)
app.include_router(student_api.router, prefix=API_PREFIX)
app.include_router(score_api.router, prefix=API_PREFIX)
app.include_router(past_experience_api.router, prefix=API_PREFIX)
app.include_router(employment_record_api.router, prefix=API_PREFIX)
app.include_router(statistics_api.router, prefix=API_PREFIX)


@app.get("/", tags=["系统"], summary="首页")
def index():
    data = {"name": "沃林学生管理系统 API", "version": "1.3.0", "docs": "/docs", "redoc": "/redoc"}
    return {"code": 0, "message": "success", "data": data}


@app.get(API_PREFIX + "/health", tags=["系统"], summary="健康检查（会检测数据库连接）")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"code": 0, "message": "success", "data": {"status": "ok"}}
