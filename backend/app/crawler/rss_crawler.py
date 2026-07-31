"""RSS 爬虫模块：抓取各行业资讯，去重后入库

工作流程：
1. 读取 rss_sources.py 中的 RSS 源配置
2. 用 urllib 下载 RSS 内容（带超时控制），再用 feedparser 解析
3. 提取标题、链接、摘要、发布时间
4. 按 source_url 去重（已入库的跳过）
5. 新文章写入 articles 表（summary/detail 留空，待 AI 模块填充）

注意版权合规：只存标题+摘要+原文链接，不全文转载。
"""
import logging
from datetime import datetime
from time import mktime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

import feedparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawler.rss_sources import RSS_SOURCES
from app.database import SessionLocal
from app.models import Article, Industry

logger = logging.getLogger(__name__)


def _fetch_rss_content(url: str, timeout: int = 10) -> str | None:
    """用 urllib 下载 RSS 内容，带超时控制

    feedparser.parse() 的 timeout 参数在部分版本不生效，
    所以先用 urllib 下载（可控超时），再交给 feedparser 解析。
    """
    try:
        req = Request(url, headers={"User-Agent": "SenbaiBot/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            # 读取并解码
            raw = resp.read()
            # 尝试常见编码
            for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="ignore")
    except (URLError, HTTPError, TimeoutError, OSError) as e:
        logger.warning("下载 RSS 失败 [%s]: %s", url, e)
        return None
    except Exception as e:
        logger.warning("下载 RSS 异常 [%s]: %s", url, e)
        return None


def _parse_published(entry) -> datetime | None:
    """从 feedparser 的 entry 中解析发布时间，失败返回 None"""
    try:
        # feedparser 提供了 published_parsed 或 updated_parsed
        time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if time_struct:
            return datetime.fromtimestamp(mktime(time_struct))
    except Exception:
        pass
    return None


def _clean_html(text: str | None) -> str:
    """简单去除 HTML 标签（RSS 摘要里常带 HTML）"""
    if not text:
        return ""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    return clean.strip()[:2000]  # 截断，避免过长


def crawl_single_source(
    db: Session,
    industry_id: int,
    source_name: str,
    rss_url: str,
) -> int:
    """抓取单个 RSS 源，返回新增文章数量

    参数：
        db: 数据库会话
        industry_id: 行业 ID
        source_name: 来源名称（如"机器之心"）
        rss_url: RSS 订阅地址
    返回：
        本次新增的文章数量
    """
    try:
        # feedparser 直接解析 URL（在云容器内验证可用）
        feed = feedparser.parse(rss_url)

        if feed.bozo and not feed.entries:
            logger.warning("RSS 解析失败 [%s]: %s", source_name, feed.bozo_exception)
            return 0

        new_count = 0
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue

            # 去重：检查 source_url 是否已存在
            existing = db.execute(
                select(Article).where(Article.source_url == link)
            ).scalar_one_or_none()

            if existing:
                continue  # 已入库，跳过

            # 提取摘要并清洗 HTML
            raw_content = _clean_html(entry.get("summary", ""))

            # 解析发布时间
            published_at = _parse_published(entry)

            # 入库（summary 和 detail 留空，待 AI 模块填充）
            db.add(Article(
                industry_id=industry_id,
                title=title,
                source_url=link,
                source_name=source_name,
                raw_content=raw_content,
                summary=None,
                detail=None,
                published_at=published_at,
            ))
            new_count += 1

        if new_count > 0:
            db.commit()
            logger.info("  [%s] 新增 %d 篇", source_name, new_count)

        return new_count

    except Exception as e:
        logger.exception("抓取 RSS 失败 [%s %s]: %s", source_name, rss_url, e)
        return 0


def crawl_all_industries():
    """抓取所有行业的资讯（定时任务调用）

    遍历 RSS_SOURCES 配置，逐个行业、逐个 RSS 源抓取。
    返回总新增文章数。
    """
    logger.info("===== 开始抓取行业资讯 =====")
    total_new = 0

    db = SessionLocal()
    try:
        # 取出所有行业，建立"名称→ID"映射
        industries = db.execute(select(Industry)).scalars().all()
        industry_map = {ind.name: ind.id for ind in industries}

        for industry_name, sources in RSS_SOURCES.items():
            industry_id = industry_map.get(industry_name)
            if not industry_id:
                logger.warning("行业 '%s' 在数据库中不存在，跳过", industry_name)
                continue

            logger.info("正在抓取行业: %s（%d 个源）", industry_name, len(sources))
            for source in sources:
                count = crawl_single_source(
                    db, industry_id, source["name"], source["url"]
                )
                total_new += count

    finally:
        db.close()

    logger.info("===== 抓取完成，共新增 %d 篇资讯 =====", total_new)
    return total_new
