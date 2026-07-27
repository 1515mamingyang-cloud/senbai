"""插入测试资讯数据（用于在没有 RSS 源的情况下测试完整流程）

用法：python seed_test_articles.py
"""
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models import Article, Industry

# 测试资讯列表（标题, 来源, 内容摘要, 行业名称）
TEST_ARTICLES = [
    # 半导体
    ("台积电3nm工艺量产，性能提升15%功耗降低30%", "半导体行业观察",
     "台积电宣布3nm工艺正式量产，首批产能将供应用于高性能计算和智能手机芯片。相比5nm，3nm工艺在相同功耗下性能提升15%，在相同性能下功耗降低30%。",
     "半导体"),
    ("中芯国际7nm工艺取得突破，国产芯片制造迈出关键一步", "钛媒体",
     "中芯国际在7nm工艺节点上取得重要进展，预计将于下半年开始小批量试产。这一突破标志着中国大陆在先进制程上的能力提升。",
     "半导体"),

    # 新能源
    ("宁德时代发布新一代麒麟电池，续航突破1000公里", "36氪",
     "宁德时代正式发布第三代CTP麒麟电池，体积利用率突破72%，能量密度达255Wh/kg，搭载该电池的电动汽车续航可突破1000公里。",
     "新能源"),
    ("光伏组件价格跌破1元/W，行业进入洗牌期", "北极星电力网",
     "随着产能持续释放，光伏组件价格已跌破1元/W的历史低点。业内人士分析，这将加速行业洗牌，中小企业面临出清压力。",
     "新能源"),

    # 人工智能
    ("OpenAI发布GPT-5，多模态推理能力大幅提升", "机器之心",
     "OpenAI正式发布GPT-5模型，在数学推理、代码生成和多模态理解方面均有显著提升。新模型支持原生图像输入和音频处理，API价格较GPT-4降低50%。",
     "人工智能"),
    ("国产大模型百团大战：通义千问、智谱GLM、Kimi三强格局初现", "量子位",
     "2024年国产大模型竞争进入白热化阶段，阿里通义千问、智谱GLM、月之暗面Kimi三家企业凭借差异化的技术路线和商业模式，形成了第一梯队。",
     "人工智能"),

    # 生物医药
    ("FDA批准首款CRISPR基因编辑疗法上市", "动脉网",
     "美国FDA正式批准全球首款基于CRISPR基因编辑技术的疗法Casgevy上市，用于治疗镰状细胞病。这是基因编辑技术从实验室走向临床的里程碑事件。",
     "生物医药"),

    # 消费电子
    ("苹果Vision Pro中国区开售，首日预约超10万台", "爱范儿",
     "苹果Vision Pro头显在中国区正式开售，起售价29999元。据供应链消息，首日预约量已超10万台，超出市场预期。",
     "消费电子"),

    # 金融科技
    ("数字人民币试点城市扩至26个，交易额破7万亿", "36氪",
     "央行数字货币研究所披露，数字人民币试点已扩展至26个城市，累计交易金额突破7万亿元。跨境支付场景成为下一阶段重点推进方向。",
     "金融科技"),

    # 航空航天
    ("SpaceX星舰第五次试飞成功，首次实现筷子塔回收", "航天爱好者网",
     "SpaceX星舰完成第五次试飞，首次成功使用发射塔机械臂回收超重型助推器。这一技术突破将大幅降低航天发射成本。",
     "航空航天"),

    # 智能制造
    ("特斯拉人形机器人Optimus进入工厂试产，量产计划2025年", "高工机器人",
     "特斯拉在财报会议上展示Optimus人形机器人在工厂内的实际工作场景，马斯克表示2025年将开始小批量量产，目标年产能50万台。",
     "智能制造"),
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        # 检查是否已有测试数据
        existing = db.execute(select(Article)).scalars().all()
        if existing:
            print(f"资讯表已有 {len(existing)} 条数据，跳过插入")
            return

        # 建立行业名称→ID映射
        industries = db.execute(select(Industry)).scalars().all()
        industry_map = {ind.name: ind.id for ind in industries}

        now = datetime.utcnow()
        for i, (title, source, content, industry_name) in enumerate(TEST_ARTICLES):
            industry_id = industry_map.get(industry_name)
            if not industry_id:
                print(f"警告：行业 '{industry_name}' 不存在，跳过")
                continue

            db.add(Article(
                industry_id=industry_id,
                title=title,
                source_url=f"https://example.com/test/{i+1}",  # 测试用 URL
                source_name=source,
                raw_content=content,
                summary=None,  # 待 AI 总结
                detail=None,
                published_at=now - timedelta(hours=i),  # 每篇错开时间
            ))

        db.commit()
        print(f"✅ 已插入 {len(TEST_ARTICLES)} 篇测试资讯")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
