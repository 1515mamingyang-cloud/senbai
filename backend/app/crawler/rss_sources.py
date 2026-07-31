"""RSS 源配置：通用科技资讯源

设计变更（v2）：
- 不再按行业分组，改为通用列表
- 爬虫阶段不区分行业，AI总结时再做行业分类
- 好处：源少而精，AI全局视野挑大事，留口子支持未来关键词/个性化

可用性验证（2026-07）：
- 36氪 / 钛媒体 / 爱范儿 / 少数派：HTTP 200，稳定
- 机器之心 / 北极星电力：HTTP 302，feedparser 能自动跟随

max_items 说明：
- 从 5-8 提升到 20，一次性多抓历史文章入库
- RSS 源通常只返回最近 10-30 条，20 足够覆盖大部分历史
"""

# 通用 RSS 源列表（不按行业分，AI会在总结阶段做行业分类）
RSS_SOURCES = [
    {"name": "36氪", "url": "https://36kr.com/feed", "max_items": 20},
    {"name": "钛媒体", "url": "https://www.tmtpost.com/feed", "max_items": 20},
    {"name": "爱范儿", "url": "https://www.ifanr.com/feed", "max_items": 20},
    {"name": "少数派", "url": "https://sspai.com/feed", "max_items": 20},
    {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss", "max_items": 20},
    {"name": "北极星电力", "url": "https://news.bjx.com.cn/rss/news.xml", "max_items": 20},
]
