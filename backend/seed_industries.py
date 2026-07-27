"""初始化行业数据脚本：预置一批行业，供用户选择关注

用法：python seed_industries.py
"""
from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models import Industry

# 预置行业列表（后续可在数据库里增删）
DEFAULT_INDUSTRIES = [
    ("半导体", "芯片设计与制造、半导体设备与材料"),
    ("新能源", "光伏、风电、储能、新能源汽车产业链"),
    ("人工智能", "大模型、AI 应用、算力基础设施"),
    ("生物医药", "创新药、医疗器械、基因技术"),
    ("消费电子", "手机、可穿戴、智能家居"),
    ("金融科技", "支付、数字货币、财富管理科技"),
    ("航空航天", "商业航天、低空经济、无人机"),
    ("智能制造", "工业机器人、3D 打印、工业互联网"),
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        existing = db.execute(select(Industry)).scalars().all()
        if existing:
            print(f"行业表已有 {len(existing)} 条数据，跳过初始化")
            return
        for name, desc in DEFAULT_INDUSTRIES:
            db.add(Industry(name=name, description=desc))
        db.commit()
        print(f"✅ 已初始化 {len(DEFAULT_INDUSTRIES)} 个行业")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
