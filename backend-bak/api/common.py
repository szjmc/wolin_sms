"""认证和接口层公共工具。"""
import re
from decimal import ROUND_HALF_UP, Decimal

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from scheme.common import ErrorResponse


_BEARER_PATTERN = re.compile(r"^Bearer\s+([a-fA-F0-9]{48})$")


def find_user_by_token(db: Session, token: str):
    """根据令牌查询启用中的用户。"""

    from dao import user_dao

    return user_dao.get_user_by_token(db, token)


def require_user_by_header(db: Session, authorization: str | None):
    """严格解析 Authorization: Bearer <48位token>，失败返回 401。"""

    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录")
    match = _BEARER_PATTERN.fullmatch(authorization.strip())
    if not match:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    user = find_user_by_token(db, match.group(1))
    if user is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user


def get_current_user(
    authorization: str | None = Header(default=None, description="Authorization: Bearer <登录令牌>"),
    db: Session = Depends(get_db),
):
    """FastAPI 认证依赖。"""

    return require_user_by_header(db, authorization)


ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "业务规则不满足（code=40001）"},
    401: {"model": ErrorResponse, "description": "未登录或令牌失效（code=40101）"},
    403: {"model": ErrorResponse, "description": "没有权限（code=40301）"},
    404: {"model": ErrorResponse, "description": "记录不存在或已删除（code=40401）"},
    409: {"model": ErrorResponse, "description": "数据冲突（code=40901）"},
    422: {"model": ErrorResponse, "description": "请求参数校验失败（code=42201）"},
}


def success(data=None):
    """组装统一成功响应。"""

    return {"code": 0, "message": "success", "data": data}


def page_data(items, total, page, page_size):
    """组装前端约定的分页响应。"""

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def round_2(value):
    """旧就业接口需要的两位小数工具，避免公共模块接入后破坏其导入。"""

    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_annualized_salary(salary_amount, salary_period):
    """旧就业接口需要的年薪换算工具。"""

    if salary_amount is None:
        return None
    if salary_period == "MONTH":
        return round_2(salary_amount * 12)
    return round_2(salary_amount)
