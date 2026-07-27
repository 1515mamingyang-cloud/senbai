"""手动触发爬虫 + AI 总结（测试用）

用法：
    python run_crawl.py          # 只抓取
    python run_crawl.py --ai     # 抓取 + AI 总结
    python run_crawl.py --ai-only  # 只 AI 总结（不抓取）
"""
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def main():
    run_ai = "--ai" in sys.argv or "--ai-only" in sys.argv
    run_crawl = "--ai-only" not in sys.argv

    if run_crawl:
        print("\n===== 第一步：抓取资讯 =====\n")
        from app.crawler.rss_crawler import crawl_all_industries
        count = crawl_all_industries()
        print(f"\n抓取完成，新增 {count} 篇资讯\n")

    if run_ai:
        print("\n===== 第二步：AI 总结 =====\n")
        from app.ai.summarizer import summarize_pending_articles
        count = summarize_pending_articles()
        print(f"\nAI 总结完成，处理 {count} 篇资讯\n")


if __name__ == "__main__":
    main()
