"""定时任务调度器：每天定时触发爬虫抓取 + AI 总结

使用 BackgroundScheduler（同步模式），不依赖 asyncio。
工作流程：每天定时 → 爬虫抓取资讯 → AI 总结生成解读
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _daily_crawl_job():
    """每日定时任务：抓取资讯 → AI 总结

    先抓取新资讯入库，再对未总结的资讯调用 AI 生成解读。
    """
    logger.info("定时抓取任务触发")
    try:
        # 第一步：爬虫抓取
        from app.crawler.rss_crawler import crawl_all_industries
        new_count = crawl_all_industries()
        logger.info("抓取完成，新增 %d 篇", new_count)

        # 第二步：AI 总结（对新入库的 + 之前未总结的）
        from app.ai.summarizer import summarize_pending_articles
        summarized = summarize_pending_articles()
        logger.info("AI 总结完成，处理 %d 篇", summarized)

    except Exception as e:
        logger.exception("定时任务执行失败: %s", e)


def start_scheduler():
    """启动调度器，注册每日定时任务"""
    global _scheduler
    _scheduler = BackgroundScheduler()

    # 每天 crawl_cron_hour 点执行
    _scheduler.add_job(
        _daily_crawl_job,
        "cron",
        hour=settings.crawl_cron_hour,
        id="daily_crawl",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("定时任务调度器已启动，每日 %d 点抓取", settings.crawl_cron_hour)
