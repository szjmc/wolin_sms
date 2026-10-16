"""
DAO 公共小工具：只放两个最常用的函数，保持简单直白。

1. clean_text：清洗文本筛选条件（去空格，空字符串按“没填”处理）
2. paginate：统一分页（先查总数，再取当前页）

为什么需要这两个函数：
以前每个分页查询都要重复写一遍“查总数 + 算偏移 + 取一页”的代码，
现在统一收拢到 paginate 里，各模块只关心自己的筛选条件，不容易写错。
"""


def clean_text(value):
    """
    清洗文本筛选条件。
    - 没传（None）→ 返回 None，表示不按这个条件筛选
    - 传了空白字符串（""、"   "）→ 也返回 None，前端空输入框不会误伤查询
    - 正常文本 → 去掉首尾空格后返回
    """
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text


def paginate(query, page, page_size):
    """
    统一分页：返回 (当前页数据列表, 总条数)。

    注意：调用 paginate 之前，调用方要先排好序（query.order_by(...)），
    否则同一页每次刷新可能看到不一样的数据。
    """
    # 先统计总数（注意：count 之前不要加 offset/limit，否则总数就错了）
    total = query.count()
    # 再跳过前面的页，取出当前页的数据
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
