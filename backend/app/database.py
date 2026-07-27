"""数据库初始化：SQLAlchemy 同步模式

同时支持 SQLite（本地开发）和 MySQL（微信云托管生产）。
根据 DATABASE_URL 自动判断使用哪种数据库。
"""
import time
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

logger = logging.getLogger(__name__)


def _create_engine_with_retry(url: str, retries: int = 5, delay: int = 3):
    """创建数据库引擎，带重试（云托管启动时 MySQL 可能还没就绪）"""
    # SQLite 和 MySQL 的连接参数不同
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}

    engine_kwargs = {
        "echo": False,
        "connect_args": connect_args,
    }

    # MySQL 额外配置：连接池预检 + 自动回收（防止长连接断开）
    if not is_sqlite:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 3600

    for attempt in range(1, retries + 1):
        try:
            engine = create_engine(url, **engine_kwargs)
            # 测试连接是否可用
            with engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            logger.info(f"数据库连接成功: {url.split('@')[-1] if '@' in url else 'sqlite'}")
            return engine
        except Exception as e:
            logger.warning(f"数据库连接失败(第{attempt}次): {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                logger.error(f"数据库连接重试{retries}次后仍失败，退出")
                raise


# 创建引擎
engine = _create_engine_with_retry(settings.database_url)

# 同步会话工厂
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 所有模型的基类
Base = declarative_base()


def get_db():
    """依赖注入：每个请求获取一个独立的数据库会话，用完自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """启动时自动建表（表不存在才创建）"""
    Base.metadata.create_all(bind=engine)


def is_mysql() -> bool:
    """当前是否使用 MySQL"""
    return settings.database_url.startswith("mysql")
