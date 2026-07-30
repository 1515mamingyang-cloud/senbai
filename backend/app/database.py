"""数据库初始化：SQLAlchemy 同步模式

同时支持 SQLite（本地开发）和 MySQL（微信云托管生产）。
根据 DATABASE_URL 自动判断使用哪种数据库。
MySQL 连接失败时自动回退到 SQLite，保证服务可用。
"""
import time
import logging
import re

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

logger = logging.getLogger(__name__)


def _ensure_mysql_database_exists(url: str):
    """连接 MySQL 服务器，如果目标数据库不存在则自动创建"""
    # 从 mysql+pymysql://user:pass@host:port/dbname?charset=utf8mb4
    # 提取出不含 dbname 的服务器 URL 和 dbname
    match = re.match(r'(mysql\+\w+://[^@]+@[^/]+/)([^?]+)(\?.*)?', url)
    if not match:
        return  # 格式不匹配，跳过

    server_url = match.group(1).rstrip('/')  # mysql+pymysql://user:pass@host:port
    db_name = match.group(2)
    params = match.group(3) or ""

    try:
        # 连接 MySQL 服务器（不指定数据库）
        server_engine = create_engine(server_url + params)
        with server_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        server_engine.dispose()
        logger.info(f"MySQL 数据库 '{db_name}' 已确认存在（不存在则已自动创建）")
    except Exception as e:
        logger.warning(f"自动创建 MySQL 数据库失败（不影响后续重试）: {e}")


def _create_engine_with_retry(url: str, retries: int = 5, delay: int = 3):
    """创建数据库引擎，带重试（云托管启动时 MySQL 可能还没就绪）

    MySQL 连接失败时自动回退到 SQLite，保证服务可用。
    """
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}

    engine_kwargs = {
        "echo": False,
        "connect_args": connect_args,
    }

    # MySQL 额外配置：连接池预检 + 自动回收
    if not is_sqlite:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 3600
        # 先确保数据库存在
        _ensure_mysql_database_exists(url)

    for attempt in range(1, retries + 1):
        try:
            engine = create_engine(url, **engine_kwargs)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"数据库连接成功: {url.split('@')[-1] if '@' in url else 'sqlite'}")
            return engine
        except Exception as e:
            logger.warning(f"数据库连接失败(第{attempt}次): {e}")
            if attempt < retries:
                time.sleep(delay)

    # MySQL 重试耗尽 → 回退到 SQLite，不让服务崩溃
    if not is_sqlite:
        logger.error(f"MySQL 连接重试{retries}次后仍失败，回退到 SQLite")
        fallback_url = "sqlite:///./senbai.db"
        engine = create_engine(fallback_url, echo=False, connect_args={"check_same_thread": False})
        settings.database_url = fallback_url  # 更新全局配置
        logger.info("已回退到 SQLite（注意：容器重启数据会丢失）")
        return engine

    raise RuntimeError(f"数据库连接失败: {url}")


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
