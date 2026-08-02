"""资讯路由：每日精选、资讯详情、反馈、收藏、手动刷新

v2 改动：
- 新增 GET /digest 接口：返回当天各行业精选大事
- 刷新逻辑改为：爬虫(crawl_all_sources) → AI批量总结(generate_daily_digest)
- test-crawl 适配新的通用 RSS 源格式
"""
import json
import logging
import threading
import time
from datetime import date, datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Article, DailyDigest, Industry, Preference, Favorite, UserIndustry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/articles", tags=["资讯"])

# ========== 手动刷新的异步状态管理 ==========
_refresh_state = {
    "running": False,
    "start_time": 0,
    "new_articles": 0,
    "digest_count": 0,
    "error": "",
    "done": False,
}
_refresh_lock = threading.Lock()


def _do_refresh_background():
    """后台线程：爬取 + AI批量总结"""
    global _refresh_state
    try:
        from app.crawler.rss_crawler import crawl_all_sources
        articles = crawl_all_sources()
        logger.info("后台刷新：抓取完成，新增 %d 篇", len(articles))

        with _refresh_lock:
            _refresh_state["new_articles"] = len(articles)

        from app.ai.summarizer import generate_daily_digest
        digest_count = generate_daily_digest(articles)
        logger.info("后台刷新：AI总结完成，生成 %d 条精选", digest_count)

        with _refresh_lock:
            _refresh_state["digest_count"] = digest_count
            _refresh_state["done"] = True
            _refresh_state["running"] = False

    except Exception as e:
        logger.exception("后台刷新失败: %s", e)
        with _refresh_lock:
            _refresh_state["error"] = str(e)
            _refresh_state["done"] = True
            _refresh_state["running"] = False


# ========== 数据模型 ==========

class FeedbackRequest(BaseModel):
    feedback: int


class InsightItem(BaseModel):
    point: str
    description: str


class DigestItem(BaseModel):
    """单条精选大事"""
    id: int
    article_id: int
    title: str
    summary: str
    insights: List[InsightItem] = []
    source_name: str | None
    source_url: str | None
    published_at: datetime | None
    rank: int
    date: str | None = None


class DigestGroup(BaseModel):
    """单个行业的精选列表"""
    industry_id: int
    industry_name: str
    items: List[DigestItem] = []


# ========== 固定路径路由（必须在 /{article_id} 之前）==========

@router.get("/digest", summary="获取每日精选大事")
def get_digest(
    target_date: str | None = Query(None, description="日期 YYYY-MM-DD，不传则返回最近5天"),
    days: int = Query(5, ge=1, le=30, description="最近几天（不传target_date时生效）"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回指定日期或最近N天的 AI 精选大事

    不传 target_date 时，默认查最近 days 天（默认5天），多天数据按行业合并。
    """
    from datetime import timedelta

    if target_date:
        try:
            query_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            query_dates = [query_date]
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
    else:
        today = date.today()
        query_dates = [today - timedelta(days=i) for i in range(days)]

    # 查这些天的所有精选，按日期倒序
    digests = db.execute(
        select(DailyDigest)
        .where(DailyDigest.date.in_(query_dates))
        .order_by(DailyDigest.date.desc(), DailyDigest.industry_id, DailyDigest.rank)
    ).scalars().all()

    if not digests:
        return {"dates": [], "industries": [], "msg": "暂无精选资讯"}

    # 按行业分组
    industry_ids = list({d.industry_id for d in digests})
    industries = db.execute(
        select(Industry).where(Industry.id.in_(industry_ids))
    ).scalars().all()
    industry_map = {ind.id: ind.name for ind in industries}

    # 收集有数据的日期
    available_dates = sorted(list({str(d.date) for d in digests}), reverse=True)

    groups = []
    for ind_id in industry_ids:
        items = []
        for d in digests:
            if d.industry_id != ind_id:
                continue
            # 关联原始文章
            article = db.execute(
                select(Article).where(Article.id == d.article_id)
            ).scalar_one_or_none()

            # 解析 insights JSON
            insights = []
            if d.ai_insights:
                try:
                    raw = json.loads(d.ai_insights)
                    insights = [
                        InsightItem(point=i.get("point", ""), description=i.get("description", ""))
                        for i in raw if isinstance(i, dict)
                    ]
                except (json.JSONDecodeError, TypeError):
                    pass

            items.append(DigestItem(
                id=d.id,
                article_id=d.article_id,
                title=article.title if article else "(文章已删除)",
                summary=d.ai_summary or "",
                insights=insights,
                source_name=article.source_name if article else None,
                source_url=article.source_url if article else None,
                published_at=article.published_at if article else None,
                rank=d.rank,
                date=str(d.date),
            ))

        groups.append(DigestGroup(
            industry_id=ind_id,
            industry_name=industry_map.get(ind_id, "未知"),
            items=items,
        ))

    return {"dates": available_dates, "industries": groups}


@router.post("/refresh", summary="手动刷新：爬取+AI总结（异步）")
def refresh_articles(
    user=Depends(get_current_user),
):
    """手动触发：爬取最新资讯 → AI批量总结生成精选

    接口立即返回，后台线程执行。通过 GET /refresh/status 轮询进度。
    """
    global _refresh_state
    with _refresh_lock:
        if _refresh_state["running"]:
            return {"msg": "刷新正在进行中", "status": "running"}

        _refresh_state = {
            "running": True,
            "start_time": time.time(),
            "new_articles": 0,
            "digest_count": 0,
            "error": "",
            "done": False,
        }

    thread = threading.Thread(target=_do_refresh_background, daemon=True)
    thread.start()

    return {"msg": "刷新已开始，请稍后查询状态", "status": "running"}


@router.get("/refresh/status", summary="查询刷新进度")
def refresh_status(
    user=Depends(get_current_user),
):
    with _refresh_lock:
        state = dict(_refresh_state)

    if state["error"]:
        return {"status": "error", "error": state["error"], **state}
    elif state["done"]:
        return {"status": "done", **state}
    elif state["running"]:
        elapsed = int(time.time() - state["start_time"])
        return {"status": "running", "elapsed": elapsed, **state}
    else:
        return {"status": "idle", "msg": "尚未发起刷新"}


@router.get("/test-crawl", summary="诊断：测试RSS源连通性")
def test_crawl(
    user=Depends(get_current_user),
):
    """从容器内部测试 RSS 源连通性"""
    import feedparser
    from app.crawler.rss_sources import RSS_SOURCES

    results = []
    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            entry_count = len(feed.entries)
            error = ""
            if feed.bozo and not feed.entries:
                error = str(feed.bozo_exception)
            results.append({
                "source": source["name"],
                "url": source["url"],
                "entries": entry_count,
                "error": error,
            })
        except Exception as e:
            results.append({
                "source": source["name"],
                "url": source["url"],
                "entries": 0,
                "error": str(e),
            })

    return {"results": results}


# ========== 原始资讯列表（保留，但不是主要展示）==========

@router.get("", summary="资讯流（原始列表）")
def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    total = db.execute(select(func.count(Article.id))).scalar()
    rows = db.execute(
        select(Article)
        .order_by(desc(Article.crawled_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return {
        "items": [{"id": a.id, "title": a.title, "source_name": a.source_name,
                    "published_at": a.published_at} for a in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ========== 参数路径路由 ==========

@router.get("/{article_id}", summary="资讯详情")
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    article = db.execute(
        select(Article).where(Article.id == article_id)
    ).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="资讯不存在")

    # 查询 DailyDigest 表，获取 AI 深度解读（insights）
    digest = db.execute(
        select(DailyDigest).where(DailyDigest.article_id == article_id)
    ).scalar_one_or_none()

    insights = []
    if digest and digest.ai_insights:
        try:
            raw = json.loads(digest.ai_insights)
            insights = [
                InsightItem(point=i.get("point", ""), description=i.get("description", ""))
                for i in raw if isinstance(i, dict)
            ]
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": article.id,
        "title": article.title,
        "summary": article.summary,
        "detail": article.detail,
        "raw_content": article.raw_content,
        "insights": [ii.model_dump() for ii in insights],
        "source_name": article.source_name,
        "source_url": article.source_url,
        "industry_id": article.industry_id,
        "published_at": article.published_at,
    }


@router.post("/{article_id}/feedback", summary="喜欢/不喜欢反馈")
def feedback(
    article_id: int,
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    existing = db.execute(
        select(Preference).where(
            Preference.user_id == user.id,
            Preference.article_id == article_id,
        )
    ).scalar_one_or_none()

    if req.feedback == 0:
        if existing:
            db.delete(existing)
            db.commit()
        return {"msg": "已取消反馈"}
    else:
        if existing:
            existing.feedback = req.feedback
        else:
            db.add(Preference(user_id=user.id, article_id=article_id, feedback=req.feedback))
        db.commit()
    return {"msg": "反馈已记录"}


@router.post("/{article_id}/favorite", summary="收藏/取消收藏")
def toggle_favorite(
    article_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    existing = db.execute(
        select(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.article_id == article_id,
        )
    ).scalar_one_or_none()

    if existing:
        db.delete(existing)
        db.commit()
        return {"msg": "已取消收藏", "favorited": False}
    else:
        db.add(Favorite(user_id=user.id, article_id=article_id))
        db.commit()
        return {"msg": "已收藏", "favorited": True}
