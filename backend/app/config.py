"""配置模块：从 .env 读取所有可调参数

支持两种数据库：
- 本地开发：SQLite（零配置，DATABASE_URL=sqlite:///./senbai.db）
- 云托管生产：MySQL（微信云托管自带，通过环境变量配置）
"""
import os
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---------- 数据库 ----------
    # 优先级：DATABASE_URL > MySQL 环境变量组合 > 默认 SQLite
    # 本地开发用 SQLite，云托管用 MySQL
    database_url: str = ""

    # ---------- 认证 ----------
    secret_key: str = "senbai-dev-secret-key-please-change-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7

    # ---------- 大模型 API ----------
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = "sk-61726c0c37b8430993baa26c389fa90c"
    llm_model: str = "deepseek-chat"

    # ---------- 爬虫 ----------
    crawl_cron_hour: int = 8

    # ---------- 初始管理员账号（云托管首次启动时自动创建）----------
    init_admin_username: str = ""
    init_admin_password: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def _build_database_url() -> str:
    """根据环境变量组装数据库连接串

    1. 如果设了 DATABASE_URL，直接用（本地开发或手动指定）
    2. 如果设了 MySQL 相关变量（微信云托管自动注入），组装 MySQL 连接串
    3. 都没有就回退到本地 SQLite
    """
    # 方式 1：直接指定 DATABASE_URL
    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url

    # 方式 2：微信云托管 MySQL 环境变量
    # 云托管创建 MySQL 后会注入这些变量（变量名以实际控制台显示为准）
    mysql_host = os.environ.get("MYSQL_HOST", "")
    if mysql_host:
        mysql_port = os.environ.get("MYSQL_PORT", "3306")
        mysql_user = os.environ.get("MYSQL_USER", "root")
        mysql_password = os.environ.get("MYSQL_PASSWORD", "")
        mysql_database = os.environ.get("MYSQL_DATABASE", "senbai")
        # 对密码做 URL 编码，处理 @、#、: 等特殊字符
        # 否则密码里的 @ 会被误解析为 URL 分隔符
        encoded_password = quote_plus(mysql_password)
        return (
            f"mysql+pymysql://{mysql_user}:{encoded_password}"
            f"@{mysql_host}:{mysql_port}/{mysql_database}?charset=utf8mb4"
        )

    # 方式 3：回退到本地 SQLite
    return "sqlite:///./senbai.db"


# 全局单例
settings = Settings()
settings.database_url = _build_database_url()
