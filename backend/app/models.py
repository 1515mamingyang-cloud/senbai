"""数据模型：定义所有数据库表结构

表关系说明：
- User(用户) ←→ Industry(行业)  多对多，通过 UserIndustry 关联（用户选关注的行业）
- User(用户) ←→ Article(文章)   一对多反馈，通过 Preference 记录喜欢/不喜欢
- User(用户) ←→ Article(文章)   一对多收藏，通过 Favorite 记录
- Industry ←→ Article           一对多（每个行业有多条资讯）
"""
from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, Boolean,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """用户表（后台手动创建账号，不开放注册）"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True, comment="登录用户名")
    hashed_password = Column(String(255), comment="bcrypt 哈希后的密码")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    preferences = relationship("Preference", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    industries = relationship("UserIndustry", back_populates="user", cascade="all, delete-orphan")


class Industry(Base):
    """行业表（预置一批行业，用户从中选择关注）"""
    __tablename__ = "industries"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, comment="行业名称，如'半导体'、'新能源'")
    description = Column(String(200), comment="行业简介")


class UserIndustry(Base):
    """用户-行业关联表（用户关注了哪些行业）"""
    __tablename__ = "user_industries"
    __table_args__ = (UniqueConstraint("user_id", "industry_id", name="uq_user_industry"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    industry_id = Column(Integer, ForeignKey("industries.id"))

    user = relationship("User", back_populates="industries")
    industry = relationship("Industry")


class Article(Base):
    """文章表：爬虫抓取的原始内容 + AI 生成的总结"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    industry_id = Column(Integer, ForeignKey("industries.id"), nullable=True, index=True, comment="所属行业（爬虫阶段为空，AI总结时分类）")
    title = Column(String(500), comment="资讯标题")
    source_url = Column(String(1000), comment="原文链接（版权合规：只放链接不存全文）")
    source_name = Column(String(100), comment="来源名称，如'36氪'、'钛媒体'")
    raw_content = Column(Text, comment="抓取到的原始摘要内容")
    summary = Column(Text, comment="AI 生成的一句话总结（小白能听懂）")
    detail = Column(Text, comment="AI 生成的详细产业影响解读")
    published_at = Column(DateTime, comment="资讯原始发布时间")
    crawled_at = Column(DateTime, default=datetime.utcnow, comment="抓取入库时间")

    industry = relationship("Industry")


class Preference(Base):
    """用户反馈表：喜欢(1)/不喜欢(-1)，用于建立用户画像"""
    __tablename__ = "preferences"
    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_user_article_pref"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    article_id = Column(Integer, ForeignKey("articles.id"))
    feedback = Column(Integer, comment="1=喜欢, -1=不喜欢")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="preferences")


class Favorite(Base):
    """收藏表：用户收藏的文章"""
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_user_article_fav"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    article_id = Column(Integer, ForeignKey("articles.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")


class DailyDigest(Base):
    """每日精选：AI从当天爬取的文章中，为每个行业挑选的大事

    设计说明：
    - 与 Article 分离，避免污染原始数据
    - 每天每个行业 3~5 条
    - 留好口子：未来可加 user_id 支持个性化，加 keywords 支持关键词搜索
    """
    __tablename__ = "daily_digests"

    id = Column(Integer, primary_key=True)
    date = Column(Date, index=True, comment="精选日期")
    industry_id = Column(Integer, ForeignKey("industries.id"), index=True, comment="行业")
    article_id = Column(Integer, ForeignKey("articles.id"), comment="关联原始文章")
    ai_summary = Column(String(200), comment="AI一句话总结")
    ai_insights = Column(Text, comment="AI观点JSON数组")
    rank = Column(Integer, default=0, comment="排序，1=最重要")
    created_at = Column(DateTime, default=datetime.utcnow)

    industry = relationship("Industry")
    article = relationship("Article")


class Message(Base):
    """留言板：支持公开发布和定向发布"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), comment="发送者ID")
    username = Column(String(50), comment="发送者用户名（冗余存储，避免连表查询）")
    content = Column(String(500), comment="留言内容")
    visibility = Column(String(20), default="public", comment="public=公开发布, targeted=定向发布")
    visible_to = Column(Text, nullable=True, comment="定向发布的可见用户名JSON数组，如[\"alice\",\"bob\"]")
    created_at = Column(DateTime, default=datetime.utcnow)
