"""AI 总结模块（v2）：批量总结，一次调用搞定

核心改进（省 Token）：
- 旧方案：逐篇调用 AI，N 篇 = N 次 API 调用，每次重复发 system prompt
- 新方案：把所有文章标题+摘要打包，一次 API 调用，AI 做行业分类 + 挑大事 + 生成解读

工作流程：
1. 接收爬虫返回的新文章列表
2. 把标题+摘要（截断100字）打包成文本
3. 一次 API 调用，让 AI 按行业分类、每行业挑 3-5 条大事
4. 解析 JSON，匹配回原始文章，存入 DailyDigest 表

留口子设计：
- strategy 参数支持未来扩展（关键词搜索、个性化推荐）
- DailyDigest 表与 Article 分离，未来可加 user_id / keywords 字段
"""
import json
import logging
from datetime import date

from openai import OpenAI
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Article, DailyDigest, Industry

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """懒加载 OpenAI 客户端"""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
    return _client


# ========== Prompt 设计（尽量精简，省 Token）==========

SYSTEM_PROMPT = """你是产业分析师。从资讯列表中为每个行业挑选3-5条大事并生成解读。
行业：半导体、新能源、人工智能、生物医药、消费电子、金融科技、航空航天、智能制造
规则：只选重要资讯；某行业无重要资讯则返回空数组；title必须使用资讯原始标题；summary不超过50字(小白能听懂)；insights给1-2个观点，point 10-20字，description 50-100字。
严格输出JSON(不要输出其他内容)：
{"半导体":[{"title":"原标题","summary":"一句话总结","insights":[{"point":"观点","description":"描述"}]}],"新能源":[],"人工智能":[],"生物医药":[],"消费电子":[],"金融科技":[],"航空航天":[],"智能制造":[]}"""


def _build_user_prompt(articles: list[Article]) -> str:
    """构造用户消息：把文章列表格式化为紧凑文本（省 Token）"""
    lines = ["资讯列表："]
    for i, a in enumerate(articles, 1):
        # 来源 + 标题 + 摘要截断100字
        source = a.source_name or ""
        title = a.title or ""
        summary = (a.raw_content or "")[:100]
        lines.append(f"{i}.[{source}]{title}-{summary}")
    return "\n".join(lines)


def _match_article(title: str, articles: list[Article]) -> Article | None:
    """把 AI 返回的 title 匹配回原始文章

    AI 可能轻微改了标题（空格、标点），用包含匹配兜底。
    """
    title_clean = title.strip()
    # 精确匹配
    for a in articles:
        if a.title.strip() == title_clean:
            return a
    # 包含匹配（AI可能截断了标题）
    for a in articles:
        if title_clean in a.title or a.title in title_clean:
            return a
    # 前缀匹配（取前20字比较）
    for a in articles:
        if a.title[:20] == title_clean[:20]:
            return a
    return None


def generate_daily_digest(
    articles: list[Article],
    strategy: str = "daily_highlights",
    **kwargs,
) -> int:
    """批量生成每日精选

    参数：
        articles: 爬虫返回的新文章列表
        strategy: 总结策略（留口子）
            - daily_highlights: 每日大事（当前实现）
            - keyword: 按关键词搜索（未来，kwargs传 keywords）
            - personalized: 按用户喜好（未来，kwargs传 user_id）
        **kwargs: 策略参数（预留）

    返回：生成的精选条数
    """
    if not articles:
        logger.info("没有新文章，跳过 AI 总结")
        return 0

    if not settings.llm_api_key:
        logger.warning("LLM_API_KEY 未配置，跳过 AI 总结")
        return 0

    logger.info("===== 开始批量 AI 总结（%d 篇文章）=====", len(articles))
    client = _get_client()

    # 构造 prompt
    user_prompt = _build_user_prompt(articles)

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=3000,
        )

        raw_output = response.choices[0].message.content.strip()

        # 去掉可能的 ```json ``` 包裹
        if raw_output.startswith("```"):
            raw_output = raw_output.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(raw_output)

    except json.JSONDecodeError as e:
        logger.error("AI 返回的 JSON 解析失败: %s", e)
        logger.debug("AI 原始输出: %s", raw_output[:500])
        return 0
    except Exception as e:
        logger.exception("调用 AI 失败: %s", e)
        return 0

    # 解析结果，写入 DailyDigest 表
    db = SessionLocal()
    try:
        # 取出所有行业，建立"名称→ID"映射
        industries = db.execute(select(Industry)).scalars().all()
        industry_map = {ind.name: ind.id for ind in industries}

        today = date.today()
        digest_count = 0

        # 建立 title → article_id 映射（用文章对象在内存中匹配）
        for industry_name, items in result.items():
            industry_id = industry_map.get(industry_name)
            if not industry_id:
                logger.warning("AI 返回了未知行业: %s", industry_name)
                continue

            if not isinstance(items, list):
                continue

            for rank, item in enumerate(items, 1):
                title = item.get("title", "")
                article = _match_article(title, articles)

                if not article:
                    logger.warning("无法匹配文章: %s", title[:30])
                    continue

                ai_summary = item.get("summary", "")
                insights = item.get("insights", [])
                if not isinstance(insights, list):
                    insights = []

                digest = DailyDigest(
                    date=today,
                    industry_id=industry_id,
                    article_id=article.id,
                    ai_summary=ai_summary,
                    ai_insights=json.dumps(insights, ensure_ascii=False),
                    rank=rank,
                )
                db.add(digest)
                digest_count += 1

        db.commit()
        logger.info("===== AI 总结完成，生成 %d 条精选 =====", digest_count)
        return digest_count

    except Exception as e:
        logger.exception("写入 DailyDigest 失败: %s", e)
        db.rollback()
        return 0
    finally:
        db.close()
