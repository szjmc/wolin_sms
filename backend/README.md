# 沃林学生管理系统 · 后端（FastAPI + SQLAlchemy + Pydantic v2 + MySQL）

> 基础版后端。接口契约以 `docs/` 中的 **V1.3 / V1.2** 字段定义为准（旧版本字段名一律不用）。
> 面向初级开发同学：代码刻意保持简单直白——**没有**自定义装饰器、元类、抽象基类、设计模式，
> 业务判断全部是平铺的 `if/else`，关键步骤都有中文注释。

---

## 1. 目录结构

```text
backend/
├── api/                          # 路由层：接收请求 → 业务判断 → 调用 DAO → 返回统一响应
│   ├── common.py                 #   公共工具：统一响应、年龄计算、年薪换算、错误响应文档
│   ├── class_api.py              #   班级管理
│   ├── teacher_api.py            #   老师管理
│   ├── class_teacher_api.py      #   班级老师关系
│   ├── student_api.py            #   学生管理
│   ├── score_api.py              #   学生成绩
│   ├── past_experience_api.py    #   学生过往经历
│   ├── employment_record_api.py  #   就业记录
│   └── statistics_api.py         #   统计分析
├── dao/                          # 数据访问层：只写基础的增删改查（统计 DAO 每个函数只有一条查询）
├── model/                        # SQLAlchemy ORM 模型：一张表一个文件
├── scheme/                       # Pydantic v2 模型：XxxCreate / XxxUpdate / XxxRead
├── database.py                   # Engine、SessionLocal、Base、get_db
├── main.py                       # 应用入口：建表、CORS、统一异常处理、注册路由
├── requirements.txt
└── .env.example
```

## 2. 一次请求是怎么流转的

```text
HTTP 请求
  → scheme   Pydantic 校验参数（类型、范围、日期先后），不合法直接返回 422
  → api      业务判断：记录是否存在(404)、编号是否重复(409)、修改后日期是否合理(400)
  → dao      读写数据库（普通查询都带 is_deleted == 0）
  → model    ORM 对象 ⇄ 数据表
  → api      ORM 对象转换成 XxxRead（顺便计算 age / annualized_salary）
  → 返回 {"code": 0, "message": "success", "data": ...}
```

## 3. 快速开始

```bash
# 1) 在 MySQL 8.0 中创建数据库（也可以直接执行 docs/sql/init_mysql.sql）
mysql -uroot -p -e "CREATE DATABASE wolin_student DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2) 安装依赖（Python 3.10 及以上）
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows：.venv\Scripts\activate
pip install -r requirements.txt

# 3) 配置数据库连接
cp .env.example .env                 # 然后修改 .env 里的 WOLIN_DB_URL

# 4) 启动（首次启动会自动建表）
uvicorn main:app --reload --port 8000
```

启动后访问：Swagger 文档 <http://127.0.0.1:8000/docs> ｜ ReDoc <http://127.0.0.1:8000/redoc> ｜ 健康检查 `GET /api/v1/health`

## 4. 统一约定（所有人必须遵守）

| 约定 | 说明 |
|---|---|
| 路径前缀 | 所有业务接口都在 `/api/v1` 下 |
| 成功响应 | `{"code": 0, "message": "success", "data": ...}`，组装用 `api/common.py` 的 `success()` |
| 分页 | `page` 默认 1；`page_size` 默认 20、最大 100；`data` 为 `{"items", "total", "page", "page_size"}` |
| 状态码 | 新增 201；查询/更新 200；删除 204（无响应体） |
| 错误响应 | `{"code": 业务码, "message": "...", "details": []}`，业务码 = HTTP 状态码 × 100 + 1 |
| 错误码 | 40001 业务规则不满足｜40401 不存在或已删除｜40901 编号冲突/存在关联｜42201 参数校验失败｜50001 服务器错误 |
| 抛错方式 | 在 api 层直接 `raise HTTPException(status_code=404, detail="学生不存在或已删除")`，`main.py` 会统一转换格式 |
| 逻辑删除 | DELETE 只设置 `is_deleted=1`、`deleted_at=当前时间`；普通查询和统计必须带 `is_deleted == 0` |
| 子数据可见性 | 成绩/过往经历/就业记录：自身未删除 **且** 所属学生未删除，才对普通查询可见 |
| PATCH | 必须用 `payload.model_dump(exclude_unset=True)`；必填字段不允许传 `null`（`check_not_null`） |
| 金额/分数 | 一律用 `Decimal`，JSON 中序列化为字符串（如 `"15000.00"`），避免精度问题 |
| 自动字段 | `id`、`created_at`、`updated_at`、`is_deleted`、`deleted_at`、`age`、快照字段都不接受客户端写入 |

## 5. 关键业务规则在哪里实现

| 业务规则 | 实现位置 |
|---|---|
| 年龄只存出生日期、动态计算 | `api/common.py`：`calculate_age()`、`to_student_read()` |
| "年龄大于 N 岁"筛选（走出生日期索引） | `api/common.py`：`calculate_birth_date_cutoff()` |
| 业务编号唯一（含已删除记录） | `dao/*_dao.py`：`get_xxx_by_no()` → api 层返回 409 |
| 同一学生同一考核序次只有一条有效成绩，删除后可重录 | 查改删路径：`/students/{id}/scores/{exam_no}`，按学生+考试定位，不按成绩 id |
| 成绩达标：至少一条有效成绩且全部 ≥ 80 | `dao/statistics_dao.py`：`GROUP BY` + `HAVING MIN(score) >= 80` |
| 不及格：有效成绩 < 60 的次数 ≥ 3 | `dao/statistics_dao.py`：`list_failure_counts()` |
| 一个学生多条就业记录、互不覆盖 | `model/employment_record.py`（student_id 不唯一）、`dao/employment_record_dao.py` |
| 年薪等价值：月薪 × 12 / 年薪本身 | 展示：`calculate_annualized_salary()`；排序筛选：`annualized_salary_expression()` |
| 姓名/班级快照 | `api/employment_record_api.py`：`create_employment_record()` |
| 就业时长 = Offer 日期 − 就业开放日期 | `api/statistics_api.py`：`employment_durations()`、`class_average_durations()` |
| 删除班级/老师前检查有效关联（409） | `api/class_api.py`、`api/teacher_api.py` |
| 班级老师关系不重复（PUT 幂等） | `api/class_teacher_api.py`：`add_class_teacher()` |

## 6. 新增一个模块的步骤（照着做即可）

1. `model/xxx.py`：定义 ORM 模型（主键 `BigInteger` 自增 + 4 个公共字段），并在 `model/__init__.py` 中导入。
2. `scheme/xxx.py`：定义 `XxxCreate`、`XxxUpdate`（字段全部可选 + `check_not_null`）、`XxxRead`（`from_attributes=True`）。
3. `dao/xxx_dao.py`：写 `get_xxx_by_id`、`list_xxx`、`create_xxx`、`update_xxx`、`delete_xxx`（逻辑删除）。
4. `api/xxx_api.py`：`router = APIRouter(tags=["模块名"], responses=ERROR_RESPONSES)`，每个路由声明 `response_model`。
5. `main.py`：`app.include_router(xxx_api.router, prefix=API_PREFIX)`。
6. 在 `tests/test_backend_api.py` 中补充正常流程、参数错误、逻辑删除、关键业务规则的测试。

## 7. 自动化测试

测试文件在项目根目录的 `tests/test_backend_api.py`（不放在 backend 目录内，保持后端目录结构不变）。
**必须使用专用测试库**，测试开始时会清空并重建表：

```bash
pip install pytest httpx
# 必须是 MySQL 专用测试库，不要用其它数据库
export WOLIN_TEST_DB_URL="mysql+pymysql://root:123456@127.0.0.1:3306/wolin_student_test?charset=utf8mb4"
pytest tests -v
```

每张业务表都有独立测试文件（每文件 20+ 条用例）：`test_classes.py`、`test_teachers.py`、`test_students.py`、`test_scores.py`、`test_past_experiences.py`、`test_employment.py`、`test_class_teachers.py`、`test_statistics.py`。

## 8. 常见坑

- **PATCH 用 `exclude_unset=True`，不要用 `exclude_none=True`**：后者会让"显式传 null 清空字段"失效。
- **新写的查询别忘了 `is_deleted == 0`**，关联查询时学生表也要过滤。
- **修改日期时要用"修改后的值"判断先后**：例如只改了培训结课日期，也要和数据库里的入学日期比较。
- **`create_all` 不会修改已存在的表**：改字段后需要手写 `ALTER TABLE` 并先在备份环境验证。
- **枚举字段**：请求模型设置了 `use_enum_values=True`，取出来就是普通字符串，可以直接存库。
