"""应用入口：创建 FastAPI 实例，注册路由，启动时建表 + 初始化数据 + 启动定时任务"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.database import init_db, SessionLocal
from app.config import settings
from app.models import Industry, User
from app.auth import hash_password
from app.routers import auth, articles, industries, messages
from app.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# 预置行业列表（和 seed_industries.py 保持一致）
DEFAULT_INDUSTRIES = [
    ("半导体", "芯片设计与制造、半导体设备与材料"),
    ("新能源", "光伏、风电、储能、新能源汽车产业链"),
    ("人工智能", "大模型、AI 应用、算力基础设施"),
    ("生物医药", "创新药、医疗器械、基因技术"),
    ("消费电子", "手机、可穿戴、智能家居"),
    ("金融科技", "支付、数字货币、财富管理科技"),
    ("航空航天", "商业航天、低空经济、无人机"),
    ("智能制造", "工业机器人、3D 打印、工业互联网"),
]


def init_data():
    """启动时自动初始化数据：建表 → 种行业 → 建管理员"""
    # 1. 建表
    init_db()

    # 记录环境变量读取情况（密码打码）
    logger.info(f"[init] INIT_ADMIN_USERNAME={settings.init_admin_username or '(空)'}")
    logger.info(f"[init] INIT_ADMIN_PASSWORD={'***已设***' if settings.init_admin_password else '(空)'}")
    logger.info(f"[init] LLM_API_KEY={'***已设***' if settings.llm_api_key else '(空)'}")
    logger.info(f"[init] DATABASE_URL={settings.database_url}")

    db = SessionLocal()
    try:
        # 2. 行业数据（表为空才初始化）
        existing_industries = db.execute(select(Industry)).scalars().all()
        if not existing_industries:
            for name, desc in DEFAULT_INDUSTRIES:
                db.add(Industry(name=name, description=desc))
            db.commit()
            logger.info(f"已初始化 {len(DEFAULT_INDUSTRIES)} 个行业")

        # 3. 管理员账号
        # 优先用环境变量，兜底用默认值（确保云托管一定能登录）
        admin_username = settings.init_admin_username or "mamingyang"
        admin_password = settings.init_admin_password or "123456"

        user_count = db.execute(select(User)).scalars().all()
        if not user_count:
            db.add(User(
                username=admin_username,
                hashed_password=hash_password(admin_password),
            ))
            db.commit()
            logger.info(f"已创建管理员账号: {admin_username}")
        else:
            logger.info(f"已有 {len(user_count)} 个用户，跳过创建管理员")

        # 确保额外用户存在（目前只有xiaoweining）
        # 已移除：开放注册后不再预置额外用户

        # 4. 数据库迁移：给 messages 表加 visibility + visible_to 字段
        try:
            db.execute(text("SELECT visibility FROM messages LIMIT 0"))
        except Exception:
            try:
                db.execute(text("ALTER TABLE messages ADD COLUMN visibility VARCHAR(20) DEFAULT 'public'"))
                db.execute(text("ALTER TABLE messages ADD COLUMN visible_to TEXT NULL"))
                db.commit()
                logger.info("messages表迁移：已添加 visibility + visible_to 字段")
            except Exception as e:
                logger.warning(f"messages表迁移失败（可能字段已存在）: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期：启动时初始化数据 + 启动每日定时任务 + 部署时自动爬取一次"""
    init_data()
    start_scheduler()

    # 部署时自动爬取+AI总结（后台线程，不阻塞启动）
    import threading
    def _startup_crawl():
        logger.info("部署启动：自动爬取+AI总结开始（后台执行）")
        try:
            from app.crawler.rss_crawler import crawl_all_sources
            articles = crawl_all_sources()
            logger.info("部署启动：抓取完成，新增 %d 篇", len(articles))

            from app.ai.summarizer import generate_daily_digest
            digest_count = generate_daily_digest(articles)
            logger.info("部署启动：AI总结完成，生成 %d 条精选", digest_count)
        except Exception as e:
            logger.exception("部署启动：自动爬取失败: %s", e)

    threading.Thread(target=_startup_crawl, daemon=True).start()
    yield


app = FastAPI(
    title="森柏 API",
    description="产业资讯追踪小程序后端：抓取 → AI 总结 → 展示 → 画像推荐",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS：允许小程序前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(articles.router)
app.include_router(industries.router)
app.include_router(messages.router)


@app.get("/", tags=["健康检查"])
def root():
    return {"status": "ok", "service": "森柏 API", "version": "0.1.0"}


@app.get("/debug", tags=["调试"])
def debug():
    """调试接口：查看环境变量和数据库状态（仅排查用，正式上线删除）"""
    from app.models import Industry, User
    db = SessionLocal()
    try:
        industries = db.execute(select(Industry)).scalars().all()
        users = db.execute(select(User)).scalars().all()
        return {
            "env": {
                "INIT_ADMIN_USERNAME": settings.init_admin_username or "(空)",
                "INIT_ADMIN_PASSWORD": "***" if settings.init_admin_password else "(空)",
                "LLM_API_KEY": "***" if settings.llm_api_key else "(空)",
                "DATABASE_URL": settings.database_url[:50] + "..." if len(settings.database_url) > 50 else settings.database_url,
            },
            "db": {
                "industries_count": len(industries),
                "users_count": len(users),
                "users": [u.username for u in users],
            },
        }
    finally:
        db.close()
