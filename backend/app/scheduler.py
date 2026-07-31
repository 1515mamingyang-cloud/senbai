"""定时任务调度器：每天早8点自动爬取 + AI批量总结

工作流程：
1. 每天 8:00 自动触发
2. 爬虫抓取所有通用 RSS 源（每个源取最新几条）
3. AI 批量总结：一次调用，为每个行业挑 3-5 条大事
4. 结果存入 DailyDigest 表

也支持手动触发（通过 /api/articles/refresh 接口）。
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _daily_crawl_job():
    """每日定时任务：爬取资讯 → AI批量总结"""
    logger.info("定时任务触发：开始爬取 + AI总结")
    try:
        # 第一步：爬虫抓取
        from app.crawler.rss_crawler import crawl_all_sources
        articles = crawl_all_sources()
        logger.info("抓取完成，新增 %d 篇", len(articles))

        # 第二步：AI 批量总结（一次调用搞定）
        from app.ai.summarizer import generate_daily_digest
        digest_count = generate_daily_digest(articles)
        logger.info("AI总结完成，生成 %d 条精选", digest_count)

    except Exception as e:
        logger.exception("定时任务执行失败: %s", e)


def start_scheduler():
    """启动调度器，注册每日定时任务"""
    global _scheduler
    _scheduler = BackgroundScheduler()

    _scheduler.add_job(
        _daily_crawl_job,
        "cron",
        hour=settings.crawl_cron_hour,
        id="daily_crawl",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("定时任务已启动，每日 %d 点自动爬取+AI总结", settings.crawl_cron_hour)
