"""留言板路由：支持公开发布 + 定向发布"""
import json
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
    visibility: str = "public"
    visible_to: str = ""

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("留言内容不能为空")
        if len(v) > 500:
            raise ValueError("留言不能超过500字")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v):
        v = v.strip().lower()
        if v not in ("public", "targeted"):
            raise ValueError("visibility 必须是 public 或 targeted")
        return v


@router.get("", summary="获取留言列表")
def list_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """获取留言列表：公开消息所有人可见，定向消息只有发送者和指定接收者可见"""
    # 查所有留言（留言量不大，Python 过滤更安全准确）
    all_msgs = db.execute(
        select(Message).order_by(desc(Message.created_at))
    ).scalars().all()

    # 过滤：公开 OR 自己发的 OR 自己是指定接收者
    visible_msgs = []
    for m in all_msgs:
        if m.visibility == "public" or m.visibility is None:
            visible_msgs.append(m)
        elif m.user_id == user.id:
            visible_msgs.append(m)
        elif m.visible_to:
            try:
                recipients = json.loads(m.visible_to)
                if user.username in recipients:
                    visible_msgs.append(m)
            except (json.JSONDecodeError, TypeError):
                pass

    total = len(visible_msgs)
    start = (page - 1) * page_size
    end = start + page_size
    page_msgs = visible_msgs[start:end]

    return {
        "items": [
            {
                "id": m.id,
                "username": m.username,
                "content": m.content,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M"),
                "is_mine": m.user_id == user.id,
                "visibility": m.visibility or "public",
            }
            for m in page_msgs
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
    """发送一条留言，支持公开发布和定向发布"""
    visible_to_json = ""

    if req.visibility == "targeted":
        # 解析用户名列表
        usernames = [u.strip() for u in req.visible_to.split(",") if u.strip()]
        if not usernames:
            raise HTTPException(status_code=400, detail="定向发布需要至少输入一个用户名")

        # 校验所有用户名是否存在
        not_found = []
        for uname in usernames:
            exists = db.execute(
                select(User).where(User.username == uname)
            ).scalar_one_or_none()
            if not exists:
                not_found.append(uname)

        if not_found:
            raise HTTPException(
                status_code=400,
                detail=f"用户名不存在: {', '.join(not_found)}",
            )

        visible_to_json = json.dumps(usernames, ensure_ascii=False)

    msg = Message(
        user_id=user.id,
        username=user.username,
        content=req.content,
        visibility=req.visibility,
        visible_to=visible_to_json,
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
        "visibility": msg.visibility,
    }
