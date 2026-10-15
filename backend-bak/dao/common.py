"""
DAO 公共工具
============

[补全说明] backend-bak 原缺少统一的文本筛选清洗和分页函数。本文件供现有 DAO
逐步接入，避免各模块重复实现并产生分页口径差异。
"""


def clean_text(value):
    """去除筛选文本首尾空格；None 或纯空白统一视为未提供。"""
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text


def paginate(query, page, page_size):
    """返回（当前页数据，总条数）；调用前应先完成过滤和排序。"""
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
