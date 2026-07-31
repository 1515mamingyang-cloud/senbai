"""RSS 源配置：每个行业对应哪些 RSS 订阅地址

说明：
- 这些是公开的 RSS 源，用于 MVP 阶段测试
- 实际使用时可根据需要增删，或后续改成数据库管理
- 部分源来自 RSSHub（开源 RSS 生成器，可将非 RSS 网站转为 RSS）

注意：爬取公开资讯请遵守版权法规，只存标题+摘要+原文链接，不全文转载。
"""

# 行业名称 → RSS 源列表
# 行业名称必须与 seed_industries.py 中的预置行业名称一致
RSS_SOURCES = {
    "半导体": [
        {
            "name": "半导体行业观察",
            "url": "https://rsshub.app/semipossible/articles",
        },
        {
            "name": "电子工程专辑",
            "url": "https://rsshub.app/eet-china/semiconductor",
        },
    ],
    "新能源": [
        {
            "name": "高工锂电",
            "url": "https://rsshub.app/gg-lb/news",
        },
        {
            "name": "北极星电力网",
            "url": "https://rsshub.app/bjx/power/news",
        },
    ],
    "人工智能": [
        {
            "name": "机器之心",
            "url": "https://rsshub.app/jiqizhixin/articles",
        },
        {
            "name": "量子位",
            "url": "https://rsshub.app/qbitai/news",
        },
    ],
    "生物医药": [
        {
            "name": "动脉网",
            "url": "https://rsshub.app/vcbeat/news",
        },
        {
            "name": "药明康德",
            "url": "https://rsshub.app/wuxiapptec/news",
        },
    ],
    "消费电子": [
        {
            "name": "爱范儿",
            "url": "https://rsshub.app/ifanr/articles",
        },
        {
            "name": "少数派",
            "url": "https://rsshub.app/sspai/matrix",
        },
    ],
    "金融科技": [
        {
            "name": "36氪",
            "url": "https://36kr.com/feed",
        },
        {
            "name": "钛媒体",
            "url": "https://rsshub.app/taimei/brief",
        },
    ],
    "航空航天": [
        {
            "name": "航空知识",
            "url": "https://rsshub.app/aerospaceknowledge/news",
        },
        {
            "name": "航天爱好者网",
            "url": "https://rsshub.app/loveSpaceShuttle/news",
        },
    ],
    "智能制造": [
        {
            "name": "工控网",
            "url": "https://rsshub.app/gongkong/news",
        },
        {
            "name": "高工机器人",
            "url": "https://rsshub.app/gg-robot/news",
        },
    ],
}
