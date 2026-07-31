"""资讯路由：资讯流、详情、喜欢/不喜欢、收藏、手动刷新"""
import json
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Article, Preference, Favorite, UserIndustry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/articles", tags=["资讯"])


class FeedbackRequest(BaseModel):
    feedback: int  # 1=喜欢, -1=不喜欢, 0=取消


class InsightItem(BaseModel):
    """单个观点"""
    point: str
    description: str


class ArticleBrief(BaseModel):
    id: int
    title: str
    summary: str | None
    source_name: str | None
    published_at: datetime | None

    class Config:
        from_attributes = True


class ArticleDetail(ArticleBrief):
    """详情页返回：summary 是观点句，insights 是结构化观点列表"""
    insights: List[InsightItem] = []
    source_url: str | None
    industry_id: int


@router.get("", summary="资讯流（按用户关注行业过滤）")
def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # 取出用户关注的行业 id
    user_industries = db.execute(
        select(UserIndustry.industry_id).where(UserIndustry.user_id == user.id)
    ).scalars().all()

    if not user_industries:
        return {"items": [], "total": 0, "page": page}

    # 按行业过滤 + 时间倒序
    total = db.execute(
        select(func.count(Article.id)).where(Article.industry_id.in_(user_industries))
    ).scalar()

    rows = db.execute(
        select(Article)
        .where(Article.industry_id.in_(user_industries))
        .order_by(desc(Article.published_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return {
        "items": [ArticleBrief.model_validate(a) for a in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


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

    # 解析 detail 字段（JSON 字符串）为 insights 数组
    insights = []
    if article.detail:
        try:
            raw_insights = json.loads(article.detail)
            insights = [
                InsightItem(point=item.get("point", ""), description=item.get("description", ""))
                for item in raw_insights
                if isinstance(item, dict)
            ]
        except (json.JSONDecodeError, TypeError):
            # 如果 detail 不是合法 JSON（旧数据兜底），当作单个观点
            insights = [InsightItem(point="详细解读", description=article.detail)]

    return {
        "id": article.id,
        "title": article.title,
        "summary": article.summary,
        "insights": insights,
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
    # 查是否已有反馈
    existing = db.execute(
        select(Preference).where(
            Preference.user_id == user.id,
            Preference.article_id == article_id,
        )
    ).scalar_one_or_none()

    if req.feedback == 0:
        # 取消反馈
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


@router.post("/refresh", summary="手动获取最新资讯 + AI总结")
def refresh_articles(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """手动触发：抓取最新资讯 → 调用大模型生成AI解读

    不再自动定时执行，只有用户主动点击才消耗 Token。
    """
    try:
        # 第一步：爬虫抓取
        from app.crawler.rss_crawler import crawl_all_industries
        new_count = crawl_all_industries()
        logger.info("手动刷新：抓取完成，新增 %d 篇", new_count)

        # 第二步：AI 总结（仅对未总结的新文章）
        from app.ai.summarizer import summarize_pending_articles
        summarized = summarize_pending_articles()
        logger.info("手动刷新：AI总结完成，处理 %d 篇", summarized)

        return {
            "msg": "刷新完成",
            "new_articles": new_count,
            "summarized": summarized,
        }
    except Exception as e:
        logger.exception("手动刷新失败: %s", e)
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")
