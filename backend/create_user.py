"""账号管理脚本：后台创建用户账号（不开放注册）

用法：
    python create_user.py 用户名 密码
    例：python create_user.py zhangsan mypassword123
"""
import sys

from sqlalchemy import select

from app.auth import hash_password
from app.database import SessionLocal, init_db
from app.models import User


def create_user(username: str, password: str):
    # 确保表已建好
    init_db()

    db = SessionLocal()
    try:
        # 检查是否已存在
        existing = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        if existing:
            print(f"用户 '{username}' 已存在")
            return

        # 创建账号
        db.add(User(username=username, hashed_password=hash_password(password)))
        db.commit()
        print(f"✅ 账号创建成功：{username}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python create_user.py <用户名> <密码>")
        sys.exit(1)
    create_user(sys.argv[1], sys.argv[2])
