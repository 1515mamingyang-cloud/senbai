"""RSS 源配置：每个行业对应哪些 RSS 订阅地址

说明：
- 全部使用直连 RSS 源（不依赖 RSSHub 公共实例，稳定性更好）
- 只保留经过验证可以正常访问的源
- 实际使用时可根据需要增删，或后续改成数据库管理

注意：爬取公开资讯请遵守版权法规，只存标题+摘要+原文链接，不全文转载。
"""

# 行业名称 → RSS 源列表
# 行业名称必须与 seed_industries.py 中的预置行业名称一致
RSS_SOURCES = {
    "半导体": [
        {"name": "36氪", "url": "https://36kr.com/feed"},
        {"name": "钛媒体", "url": "https://www.tmtpost.com/feed"},
    ],
    "新能源": [
        {"name": "36氪", "url": "https://36kr.com/feed"},
        {"name": "钛媒体", "url": "https://www.tmtpost.com/feed"},
    ],
    "人工智能": [
        {"name": "36氪", "url": "https://36kr.com/feed"},
        {"name": "钛媒体", "url": "https://www.tmtpost.com/feed"},
    ],
    "生物医药": [
        {"name": "36氪", "url": "https://36kr.com/feed"},
        {"name": "钛媒体", "url": "https://www.tmtpost.com/feed"},
    ],
    "消费电子": [
        {"name": "爱范儿", "url": "https://www.ifanr.com/feed"},
        {"name": "少数派", "url": "https://sspai.com/feed"},
    ],
    "金融科技": [
        {"name": "36氪", "url": "https://36kr.com/feed"},
        {"name": "钛媒体", "url": "https://www.tmtpost.com/feed"},
    ],
    "航空航天": [
        {"name": "36氪", "url": "https://36kr.com/feed"},
        {"name": "钛媒体", "url": "https://www.tmtpost.com/feed"},
    ],
    "智能制造": [
        {"name": "36氪", "url": "https://36kr.com/feed"},
        {"name": "钛媒体", "url": "https://www.tmtpost.com/feed"},
    ],
}
