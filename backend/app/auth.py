"""认证工具：密码哈希 + JWT 令牌生成

直接使用 bcrypt 库（不经过 passlib），避免 passlib 1.7.4 与 bcrypt 4.x 的兼容性问题。
"""
from datetime import datetime, timedelta

import bcrypt
from jose import jwt

from app.config import settings


def hash_password(password: str) -> str:
    """明文密码 → bcrypt 哈希值（存数据库用）"""
    # bcrypt 限制密码最长 72 字节，超长截断
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码是否匹配哈希值"""
    pwd_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(data: dict) -> str:
    """生成 JWT 令牌，data 里通常放用户 id 和用户名"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
