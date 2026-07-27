"""行业路由：行业列表、设置关注行业、收藏列表"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Industry, UserIndustry, Favorite, Article

router = APIRouter(prefix="/api", tags=["行业与收藏"])


class IndustryOut(BaseModel):
    id: int
    name: str
    description: str | None

    class Config:
        from_attributes = True


class SetIndustriesRequest(BaseModel):
    industry_ids: list[int]


@router.get("/industries", response_model=list[IndustryOut], summary="所有可选行业")
def list_industries(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = db.execute(select(Industry).order_by(Industry.id)).scalars().all()
    return rows


@router.get("/users/me/industries", response_model=list[IndustryOut], summary="我关注的行业")
def my_industries(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = db.execute(
        select(Industry)
        .join(UserIndustry, UserIndustry.industry_id == Industry.id)
        .where(UserIndustry.user_id == user.id)
    ).scalars().all()
    return rows


@router.post("/users/me/industries", summary="设置我关注的行业（覆盖式）")
def set_my_industries(
    req: SetIndustriesRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # 先删除旧的，flush 刷入数据库，再批量插入新的（覆盖式更新）
    db.execute(
        delete(UserIndustry).where(UserIndustry.user_id == user.id)
    )
    db.flush()  # 确保 DELETE 已执行，避免与新 INSERT 的唯一约束冲突

    for iid in req.industry_ids:
        db.add(UserIndustry(user_id=user.id, industry_id=iid))

    db.commit()
    return {"msg": "已更新关注行业", "count": len(req.industry_ids)}


@router.get("/users/me/favorites", summary="我的收藏列表")
def my_favorites(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = db.execute(
        select(Article, Favorite.created_at)
        .join(Favorite, Favorite.article_id == Article.id)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
    ).all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "summary": a.summary,
            "source_name": a.source_name,
            "published_at": a.published_at,
            "favorited_at": fav_created,
        }
        for a, fav_created in rows
    ]
