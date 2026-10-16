"""密码与令牌：bcrypt 加随机盐，禁止存明文；损坏哈希按登录失败处理。"""
import secrets
import bcrypt


def hash_password(plain_password: str) -> str:
    """新建和重置共用；限制 UTF-8 字节数，防止 bcrypt 静默截断。"""
    if not isinstance(plain_password, str) or len(plain_password) < 6:
        raise ValueError("密码至少需要 6 个字符")
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("密码 UTF-8 长度不能超过 72 字节")
    # 密码首尾空格有意义，不能 strip 后再加密。
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """密码不对、超出字节上限、哈希损坏时都返回 False，不引发 500。"""
    if not isinstance(plain_password, str) or not isinstance(password_hash, str):
        return False
    password_bytes = plain_password.encode("utf-8")
    if not password_bytes or len(password_bytes) > 72:
        return False
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def make_token() -> str:
    """每次登录产生新的随机令牌；恢复密码后旧令牌失效。"""
    return secrets.token_hex(24)
