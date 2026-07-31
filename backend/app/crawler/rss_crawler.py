"""RSS 爬虫模块：抓取通用科技资讯，去重后入库

工作流程（v2）：
1. 遍历 RSS_SOURCES 通用源列表
2. 用 feedparser 解析每个 RSS 源
3. 每个源只取最新 max_items 条（省存储、省后续 AI token）
4. 按 source_url 去重
5. 新文章写入 articles 表（industry_id=None，待 AI 总结时分类）

留口子：
- crawl_all_sources() 返回新文章列表，方便 AI 模块直接使用
- 未来可加关键词过滤参数，只入库包含特定关键词的文章
"""
import logging
from datetime import datetime
from time import mktime

import feedparser
from sqlalchemy import select

from app.crawler.rss_sources import RSS_SOURCES
from app.database import SessionLocal
from app.models import Article

logger = logging.getLogger(__name__)


def _parse_published(entry) -> datetime | None:
    """从 feedparser 的 entry 中解析发布时间，失败返回 None"""
    try:
        time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if time_struct:
            return datetime.fromtimestamp(mktime(time_struct))
    except Exception:
        pass
    return None


def _clean_html(text: str | None) -> str:
    """简单去除 HTML 标签（RSS 摘要里常带 HTML），截断到200字"""
    if not text:
        return ""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    return clean.strip()[:200]


def crawl_single_source(db, source_name: str, rss_url: str, max_items: int = 8) -> list[Article]:
    """抓取单个 RSS 源，返回新增的 Article 列表

    参数：
        db: 数据库会话
        source_name: 来源名称
        rss_url: RSS 订阅地址
        max_items: 最多取最新几条（省存储和AI token）
    返回：
        本次新增的 Article 对象列表
    """
    try:
        feed = feedparser.parse(rss_url)

        if feed.bozo and not feed.entries:
            logger.warning("RSS 解析失败 [%s]: %s", source_name, feed.bozo_exception)
            return []

        new_articles = []
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue

            # 去重：检查 source_url 是否已存在
            existing = db.execute(
                select(Article).where(Article.source_url == link)
            ).scalar_one_or_none()

            if existing:
                continue

            raw_content = _clean_html(entry.get("summary", ""))
            published_at = _parse_published(entry)

            article = Article(
                industry_id=None,  # 爬虫阶段不分类，AI总结时再分
                title=title,
                source_url=link,
                source_name=source_name,
                raw_content=raw_content,
                summary=None,
                detail=None,
                published_at=published_at,
            )
            db.add(article)
            new_articles.append(article)

        if new_articles:
            db.commit()
            logger.info("  [%s] 新增 %d 篇", source_name, len(new_articles))

        return new_articles

    except Exception as e:
        logger.exception("抓取 RSS 失败 [%s %s]: %s", source_name, rss_url, e)
        return []


def crawl_all_sources() -> list[Article]:
    """抓取所有通用 RSS 源（定时任务调用）

    返回所有新增的 Article 对象列表（供 AI 总结模块使用）。
    """
    logger.info("===== 开始抓取资讯 =====")
    all_new = []

    db = SessionLocal()
    try:
        for source in RSS_SOURCES:
            logger.info("正在抓取: %s", source["name"])
            articles = crawl_single_source(
                db,
                source["name"],
                source["url"],
                max_items=source.get("max_items", 8),
            )
            all_new.extend(articles)
    finally:
        db.close()

    logger.info("===== 抓取完成，共新增 %d 篇 =====", len(all_new))
    return all_new
