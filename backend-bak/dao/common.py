"""DAO 层公共小工具：文本清理和分页。"""


def clean_text(value):
    """空值或全空白按未填写处理，其余文本只清理首尾空格。"""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def paginate(query, page: int, page_size: int):
    """先统计总数，再按稳定的页码取数据。"""

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
