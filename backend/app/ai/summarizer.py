"""AI 总结模块：调用大模型，把专业资讯翻译成"小白能听懂"的总结

工作流程：
1. 查询 articles 表中 summary 为空的文章（待总结）
2. 构造 prompt，调用大模型（OpenAI 兼容接口）
3. 生成两部分内容：
   - summary：一句话观点句（小白也能听懂，不超过50字）
   - insights：1~3 个结构化观点，每个包含 point（观点标题）和 description（一段描述）
4. summary 存入 articles.summary，insights 序列化为 JSON 存入 articles.detail

支持的模型服务商（都兼容 OpenAI 接口）：
- DeepSeek: base_url=https://api.deepseek.com/v1
- 智谱 GLM: base_url=https://open.bigmodel.cn/api/paas/v4
- 通义千问: base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
- Kimi:     base_url=https://api.moonshot.cn/v1
"""
import json
import logging

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Article

logger = logging.getLogger(__name__)

# 构造大模型客户端（OpenAI 兼容接口）
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """懒加载 OpenAI 客户端（避免启动时就报错）"""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
    return _client


# ========== Prompt 设计 ==========

SYSTEM_PROMPT = """你是一个资深的产业分析师，擅长把复杂的行业新闻用通俗易懂的语言解释给外行听。

你的任务是对给定的资讯生成两部分内容：

1. summary：一句话观点句，提炼这条资讯最核心的信号，小白也能听懂，不超过50个字
2. insights：1~3 个结构化观点，每个观点包含：
   - point：观点标题（10~20字，简明扼要）
   - description：对该观点的详细解读（50~150字，说明对产业的影响、背后的逻辑）

观点的数量根据资讯的信息量决定：信息量大的资讯给3个观点，简单的给1~2个。
每个观点应该从不同角度切入（如：技术层面、市场层面、竞争格局、供应链等）。

请严格用以下 JSON 格式输出（不要输出其他内容）：
{"summary": "一句话观点句", "insights": [{"point": "观点标题1", "description": "详细描述1"}, {"point": "观点标题2", "description": "详细描述2"}]}"""

USER_PROMPT_TEMPLATE = """请总结以下资讯：

标题：{title}
来源：{source}
内容摘要：{content}"""


def _summarize_one(article: Article, client: OpenAI) -> tuple[str, str] | None:
    """调用大模型总结单篇文章

    返回 (summary, insights_json) 或 None（失败时）
    - summary: 一句话观点句
    - insights_json: insights 数组的 JSON 字符串，如 '[{"point":"...","description":"..."}]'
    """
    try:
        prompt = USER_PROMPT_TEMPLATE.format(
            title=article.title,
            source=article.source_name or "未知",
            content=article.raw_content or "（无摘要内容，请根据标题分析）",
        )

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,  # 低温度 = 更稳定、更聚焦的输出
            max_tokens=800,
        )

        raw_output = response.choices[0].message.content.strip()

        # 有时模型会在 JSON 外面包一层 ```json ... ```，需要去掉
        if raw_output.startswith("```"):
            raw_output = raw_output.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(raw_output)

        summary = result.get("summary", "")
        insights = result.get("insights", [])

        # 兜底：如果 insights 不是列表或为空，至少返回 summary
        if not isinstance(insights, list):
            insights = []

        return summary, json.dumps(insights, ensure_ascii=False)

    except json.JSONDecodeError:
        logger.warning("大模型返回的 JSON 解析失败，文章 ID=%d", article.id)
        # 降级方案：把原始输出当作 summary，无 insights
        return raw_output[:50], "[]"
    except Exception as e:
        logger.exception("调用大模型失败，文章 ID=%d: %s", article.id, e)
        return None


def summarize_pending_articles():
    """对所有未总结的资讯生成 AI 解读

    查询 summary 为空的文章，逐篇调用大模型，写回 summary 和 detail。
    detail 字段存储 insights 数组的 JSON 字符串。
    返回成功总结的文章数。
    """
    # 检查 API key 是否已配置
    if not settings.llm_api_key:
        logger.warning("LLM_API_KEY 未配置，跳过 AI 总结。请在 .env 文件中填入你的 API key。")
        return 0

    logger.info("===== 开始 AI 总结 =====")
    client = _get_client()
    success_count = 0

    db: Session = SessionLocal()
    try:
        # 查询所有 summary 为空的待总结文章，限制每次处理 50 篇
        pending = db.execute(
            select(Article).where(Article.summary.is_(None)).limit(50)
        ).scalars().all()

        if not pending:
            logger.info("没有待总结的资讯")
            return 0

        logger.info("待总结文章: %d 篇", len(pending))

        for article in pending:
            result = _summarize_one(article, client)
            if result:
                article.summary, article.detail = result
                db.commit()
                success_count += 1
                logger.info("  ✅ [ID=%d] %s", article.id, article.title[:30])
            else:
                logger.warning("  ❌ [ID=%d] 总结失败", article.id)

    finally:
        db.close()

    logger.info("===== AI 总结完成，成功 %d 篇 =====", success_count)
    return success_count
