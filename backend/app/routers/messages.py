"""留言板路由：公共留言板，所有用户异步互通"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Message, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/messages", tags=["留言板"])


class MessageCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("留言内容不能为空")
        if len(v) > 500:
            raise ValueError("留言不能超过500字")
        return v


@router.get("", summary="获取留言列表")
def list_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """获取公共留言板列表，按时间倒序，分页"""
    total = db.execute(select(func.count(Message.id))).scalar()
    rows = db.execute(
        select(Message)
        .order_by(desc(Message.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return {
        "items": [
            {
                "id": m.id,
                "username": m.username,
                "content": m.content,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M"),
                "is_mine": m.user_id == user.id,
            }
            for m in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", summary="发送留言")
def create_message(
    req: MessageCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """发送一条留言到公共留言板"""
    msg = Message(
        user_id=user.id,
        username=user.username,
        content=req.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "id": msg.id,
        "username": msg.username,
        "content": msg.content,
        "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M"),
        "is_mine": True,
    }
