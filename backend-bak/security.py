"""密码和登录令牌工具。密码只保存 bcrypt 哈希，不保存明文。"""
import secrets

import bcrypt


def _password_bytes(value: str) -> bytes | None:
    """把密码转换为 UTF-8 字节；类型错误或编码错误统一返回 None。"""

    if not isinstance(value, str):
        return None
    try:
        password_bytes = value.encode("utf-8")
    except UnicodeError:
        return None
    if not password_bytes or len(password_bytes) > 72:
        return None
    return password_bytes


def hash_password(plain_password: str) -> str:
    """使用 bcrypt 加随机盐哈希密码，并防止 bcrypt 静默截断超长密码。"""

    if not isinstance(plain_password, str) or len(plain_password) < 6:
        raise ValueError("密码至少需要 6 个字符")
    password_bytes = _password_bytes(plain_password)
    if password_bytes is None:
        raise ValueError("密码 UTF-8 长度不能超过 72 字节")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """密码错误、密码超长或数据库中的哈希损坏时都返回 False。"""

    password_bytes = _password_bytes(plain_password)
    if password_bytes is None or not isinstance(password_hash, str):
        return False
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (UnicodeError, ValueError, TypeError):
        return False


def make_token() -> str:
    """生成 48 位十六进制令牌，与前端和数据库字段约定一致。"""

    return secrets.token_hex(24)
