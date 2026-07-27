# 森柏小程序 - 部署发布指南

## 整体思路

```
小程序(体验版)  →  云服务器公网IP:8765  →  FastAPI后端
     ↑                    ↑
  手机扫码使用         跑在你的云服务器上
  开调试模式绕过HTTPS   用 systemd 守护进程常驻
```

---

## 第一步：购买腾讯云轻量应用服务器

1. 打开 https://cloud.tencent.com/product/lighthouse
2. 购买配置：
   - **地域**：选离你最近的（如广州、上海、北京）
   - **机型**：2核2G（最低够用，约 ¥60~100/月）
   - **系统镜像**：Ubuntu 22.04 LTS
   - **流量包**：默认 500GB/月 足够
3. 购买后在控制台找到 **公网 IP**（形如 `43.xxx.xxx.xxx`）
4. 记下这个 IP，后面要用

---

## 第二步：部署后端到服务器

### 2.1 登录服务器

在腾讯云控制台点击「登录」，或用本地终端 SSH：

```bash
ssh ubuntu@你的服务器IP
```

### 2.2 安装 Python 环境

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### 2.3 上传项目代码

**方法一：用 scp 上传（推荐）**

在你本地电脑（不是服务器）执行：

```bash
# 把后端代码传到服务器（在 senbai/backend/ 目录下执行）
scp -r app/ requirements.txt .env create_user.py seed_industries.py seed_test_articles.py run_crawl.py ubuntu@你的服务器IP:~/senbai/
```

**方法二：在服务器上直接 clone（如果你把代码传到了 GitHub）**

```bash
git clone 你的仓库地址 ~/senbai
cd ~/senbai
```

### 2.4 安装依赖并初始化

```bash
cd ~/senbai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 初始化数据
python seed_industries.py
python create_user.py mamingyang 123456
python create_user.py xiaoweining 123456
python seed_test_articles.py
```

### 2.5 修改 .env

```bash
nano .env
```

确认内容：
```
DATABASE_URL=sqlite:///./senbai.db
SECRET_KEY=森柏_2024_secret_key_change_in_production
LLM_API_KEY=sk-61726c0c37b8430993baa26c389fa90c
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

### 2.6 测试启动

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8765
```

用浏览器访问 `http://你的服务器IP:8765/`，看到 `{"status":"ok"}` 就成功了。

按 Ctrl+C 先停掉，下一步设置常驻。

### 2.7 设置开机自启（systemd）

```bash
sudo nano /etc/systemd/system/senbai.service
```

写入以下内容（把 `ubuntu` 和路径改成你的）：

```ini
[Unit]
Description=Senbai API Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/senbai
ExecStart=/home/ubuntu/senbai/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl start senbai
sudo systemctl enable senbai
sudo systemctl status senbai  # 查看状态，绿色 active 就对了
```

### 2.8 开放防火墙端口

腾讯云控制台 → 轻量应用服务器 → 防火墙 → 添加规则：
- 协议：TCP
- 端口：8765
- 来源：0.0.0.0/0（所有）

---

## 第三步：修改小程序 API 地址

打开 `miniprogram/utils/api.js`，把第一行的 `127.0.0.1:8765` 改成你的服务器公网 IP：

```javascript
// 改之前
const BASE_URL = 'http://127.0.0.1:8765'

// 改之后（换成你的实际 IP）
const BASE_URL = 'http://43.xxx.xxx.xxx:8765'
```

---

## 第四步：上传小程序代码设为体验版

### 4.1 上传代码

1. 打开微信开发者工具，载入 `senbai/` 项目
2. 确认右上角 AppID 是你的 `wx60f090d298e36d6b`
3. 点击工具栏右上角 **「上传」** 按钮
4. 填写版本号（如 `0.0.1`）和备注（如"首次体验版"）
5. 点击确定上传

### 4.2 设为体验版

1. 打开 https://mp.weixin.qq.com 登录小程序后台
2. 左侧菜单 → **管理** → **版本管理**
3. 在「开发版本」里找到刚上传的版本
4. 点击 **「选为体验版」**
5. 会生成一个体验版二维码

### 4.3 添加体验成员

1. 左侧菜单 → **管理** → **成员管理**
2. 在「体验成员」下点 **「添加」**
3. 输入对方的微信号，添加即可
4. 只有被添加的成员才能扫码使用体验版（最多 200 人）

---

## 第五步：手机上使用

1. 体验成员用微信扫描体验版二维码
2. 打开小程序后，点击右上角 **三个点**
3. 选择 **「开发调试」** → 开启调试模式
4. 小程序会重新加载，此时可以正常请求 HTTP 接口（绕过 HTTPS 限制）
5. 用账号密码登录，正常使用

> 注意：每个体验成员都需要单独开启调试模式，只需开一次。

---

## 后续升级：域名 + HTTPS（不急）

等你买好域名并完成 ICP 备案后：

1. 在腾讯云申请免费 SSL 证书
2. 服务器装 Nginx，配反向代理：
   ```nginx
   server {
       listen 443 ssl;
       server_name api.你的域名.com;
       ssl_certificate     /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://127.0.0.1:8765;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
3. 小程序后台 → 开发管理 → 开发设置 → 服务器域名 → 添加 `https://api.你的域名.com`
4. 小程序 API 地址改成 HTTPS 域名
5. 重新上传代码，手机上就不需要开调试模式了

---

## 常见问题

**Q: 服务器上 uvicorn 启动报错？**
A: 检查依赖是否装全了：`pip install -r requirements.txt`

**Q: 小程序连不上后端？**
A: 检查三件事：①服务器防火墙开了 8765 端口 ②uvicorn 用 `--host 0.0.0.0` 启动 ③手机开了调试模式

**Q: 定时任务在服务器上不跑？**
A: systemd 启动的服务会自动运行 APScheduler，检查 `sudo journalctl -u senbai -f` 看日志

**Q: 想看后端日志？**
A: `sudo journalctl -u senbai -f`（实时查看）或 `sudo journalctl -u senbai --since today`（今天日志）
