# 森柏 (Senbai)

产业资讯追踪小程序——定期抓取行业大事，用大白话总结产业影响。

## 技术栈

- **后端**：Python 3.13 + FastAPI + SQLite（同步）+ APScheduler
- **前端**：原生微信小程序（WXML/WXSS/JS）
- **AI**：OpenAI 兼容接口（智谱/通义/Kimi/DeepSeek 均可）

## 目录结构

```
senbai/
├── backend/                        # 后端服务
│   ├── app/
│   │   ├── main.py                 # 应用入口（注册路由、启动定时任务）
│   │   ├── config.py               # 配置（从 .env 读取）
│   │   ├── database.py             # 数据库初始化（SQLAlchemy 同步模式）
│   │   ├── models.py               # 数据模型（6 张表）
│   │   ├── auth.py                 # 密码哈希（bcrypt）+ JWT
│   │   ├── deps.py                 # 依赖注入（解析当前登录用户）
│   │   ├── scheduler.py            # 定时任务（每天抓取+AI总结）
│   │   ├── routers/                # API 路由
│   │   │   ├── auth.py             #   登录
│   │   │   ├── articles.py         #   资讯流/详情/反馈/收藏
│   │   │   └── industries.py       #   行业选择/收藏列表
│   │   ├── crawler/                # 爬虫模块
│   │   │   ├── rss_crawler.py      #   RSS 抓取逻辑
│   │   │   └── rss_sources.py      #   RSS 源配置
│   │   └── ai/                     # AI 总结模块
│   │       └── summarizer.py       #   大模型调用 + 总结生成
│   ├── create_user.py              # 创建账号脚本
│   ├── seed_industries.py          # 初始化行业数据（8个预置行业）
│   ├── seed_test_articles.py       # 插入测试资讯（11篇）
│   ├── run_crawl.py                # 手动触发抓取+AI总结
│   ├── requirements.txt
│   └── .env                        # 配置文件（需填写大模型API key）
│
├── miniprogram/                    # 微信小程序前端
│   ├── app.js / app.json / app.wxss  # 应用配置与全局样式
│   ├── utils/
│   │   └── api.js                  # API 请求封装
│   ├── pages/
│   │   ├── login/                  # 登录页
│   │   ├── index/                  # 首页（资讯流）
│   │   ├── detail/                 # 展示页（资讯详情）
│   │   ├── favorites/              # 收藏页
│   │   └── profile/                # 我的（选行业/设置）
│   └── sitemap.json
│
└── project.config.json             # 小程序项目配置
```

## 后端启动

```bash
cd backend

# 1. 创建虚拟环境（首次）
python -m venv .venv

# 2. 安装依赖（首次）
.venv/Scripts/python.exe -m pip install -r requirements.txt

# 3. 初始化行业数据（首次）
.venv/Scripts/python.exe seed_industries.py

# 4. 创建账号
.venv/Scripts/python.exe create_user.py 你的用户名 你的密码

# 5. 插入测试资讯（可选，用于没有RSS源时测试）
.venv/Scripts/python.exe seed_test_articles.py

# 6. 启动服务
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8765
```

启动后访问 http://localhost:8765/docs 可看交互式 API 文档。

## AI 总结配置

编辑 `backend/.env`，填入你的大模型 API key：

```env
LLM_BASE_URL=https://api.deepseek.com/v1   # 或智谱/通义/Kimi
LLM_API_KEY=sk-你的key
LLM_MODEL=deepseek-chat                     # 对应模型名
```

配置后可手动触发 AI 总结测试：
```bash
.venv/Scripts/python.exe run_crawl.py --ai-only
```

## 小程序使用

1. 用**微信开发者工具**打开 `senbai/` 目录
2. 在 `project.config.json` 中替换 `appid` 为你的小程序 AppID
3. 在 `miniprogram/app.js` 中确认 `apiBase` 指向后端地址（开发时用 `http://127.0.0.1:8765`）
4. 微信开发者工具中关闭「不校验合法域名」（开发阶段）

## API 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 账号密码登录，返回 JWT |
| GET  | /api/articles | 资讯流（按关注行业过滤，分页） |
| GET  | /api/articles/{id} | 资讯详情 |
| POST | /api/articles/{id}/feedback | 喜欢/不喜欢反馈 |
| POST | /api/articles/{id}/favorite | 收藏/取消收藏 |
| GET  | /api/industries | 所有可选行业 |
| GET  | /api/users/me/industries | 我关注的行业 |
| POST | /api/users/me/industries | 设置关注行业（覆盖式） |
| GET  | /api/users/me/favorites | 我的收藏列表 |

## 数据模型

| 表 | 说明 |
|----|------|
| users | 用户（后台创建，不开放注册） |
| industries | 行业（预置 8 个：半导体/新能源/人工智能等） |
| user_industries | 用户关注的行业（多对多） |
| articles | 资讯（标题+原文链接+AI总结+AI解读） |
| preferences | 用户喜欢/不喜欢反馈（建画像） |
| favorites | 用户收藏 |

## 上架说明

当前为**体验版**（内部使用），不需要微信审核：
- 上传代码 → 后台添加体验成员（微信号）→ 扫码使用
- 最多 200 名体验成员
- 后端域名需在小程序后台配置「服务器域名」白名单

如需正式公开上架（资讯类），需企业主体 + 可能需《互联网新闻信息服务许可证》等资质。

## 开发进度

- [x] 后端骨架（FastAPI + SQLite + 登录 + 路由）
- [x] 数据模型设计（6 张表）
- [x] RSS 爬虫模块（feedparser 解析 + 去重入库）
- [x] AI 总结模块（OpenAI 兼容接口 + JSON 结构化输出）
- [x] 定时任务（每天自动抓取 + AI 总结）
- [x] 小程序前端 4 个页面（登录/首页/详情/收藏/我的）
- [x] 喜欢/不喜欢反馈 + 收藏功能
- [x] 测试数据脚本（11 篇示例资讯）
- [ ] 用户画像排序（基于反馈优化推送排序）
- [ ] 微信订阅消息推送
