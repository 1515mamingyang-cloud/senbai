"""认证路由：登录 + 注册接口"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_password, create_access_token, hash_password
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("用户名至少2个字符")
        if len(v) > 30:
            raise ValueError("用户名不能超过30个字符")
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v):
        v = v.strip()
        if len(v) < 4:
            raise ValueError("密码至少4个字符")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/login", response_model=TokenResponse, summary="账号密码登录")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # 查用户
    user = db.execute(
        select(User).where(User.username == req.username)
    ).scalar_one_or_none()

    # 校验密码
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    # 签发 token
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(access_token=token, username=user.username)


@router.post("/register", response_model=TokenResponse, summary="用户注册")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户自助注册：用户名+密码，重名校验，注册成功自动返回token"""
    # 重名校验
    existing = db.execute(
        select(User).where(User.username == req.username)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已被占用",
        )

    # 创建用户
    user = User(
        username=req.username,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger = logging.getLogger(__name__)
    logger.info(f"新用户注册: {req.username}")

    # 签发 token（注册即登录）
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(access_token=token, username=user.username)
