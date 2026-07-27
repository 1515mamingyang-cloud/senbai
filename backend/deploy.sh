#!/bin/bash
# 森柏后端服务器一键部署脚本
# 用法：在服务器上执行 bash deploy.sh
# 前提：代码已上传到 ~/senbai/ 目录

set -e

echo "========================================="
echo "  森柏后端部署脚本"
echo "========================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "requirements.txt" ]; then
    echo "[错误] 请在 senbai/backend/ 目录下执行此脚本"
    echo "       或确保 requirements.txt 在当前目录"
    exit 1
fi

# 1. 安装系统依赖
echo "[1/6] 安装系统依赖..."
sudo apt update -qq
sudo apt install -y python3 python3-venv python3-pip -qq

# 2. 创建虚拟环境
echo "[2/6] 创建 Python 虚拟环境..."
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装 Python 依赖
echo "[3/6] 安装 Python 依赖..."
pip install -r requirements.txt -q

# 4. 初始化数据
echo "[4/6] 初始化数据库和测试数据..."
python seed_industries.py
python create_user.py mamingyang 123456 2>/dev/null || echo "  mamingyang 已存在"
python create_user.py xiaoweining 123456 2>/dev/null || echo "  xiaoweining 已存在"
python create_user.py testuser test123456 2>/dev/null || echo "  testuser 已存在"
python seed_test_articles.py 2>/dev/null || echo "  测试数据已存在"

# 5. 配置 systemd 守护进程
echo "[5/6] 配置 systemd 服务..."
WORK_DIR=$(pwd)
VENV_PYTHON="${WORK_DIR}/.venv/bin/python"

cat > /tmp/senbai.service << EOF
[Unit]
Description=Senbai API Server
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=${WORK_DIR}
ExecStart=${WORK_DIR}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/senbai.service /etc/systemd/system/senbai.service
sudo systemctl daemon-reload
sudo systemctl enable senbai
sudo systemctl restart senbai

# 6. 检查状态
echo "[6/6] 检查服务状态..."
sleep 2
if sudo systemctl is-active --quiet senbai; then
    echo ""
    echo "========================================="
    echo "  部署成功!"
    echo "========================================="
    echo ""
    echo "服务状态: 运行中"
    echo "API地址:  http://$(curl -s ifconfig.me):8765"
    echo ""
    echo "常用命令:"
    echo "  查看日志:   sudo journalctl -u senbai -f"
    echo "  重启服务:   sudo systemctl restart senbai"
    echo "  停止服务:   sudo systemctl stop senbai"
    echo ""
    echo "下一步:"
    echo "  1. 腾讯云控制台 → 防火墙 → 开放 TCP 8765 端口"
    echo "  2. 小程序 api.js 中把 127.0.0.1 改成上面的 IP"
    echo "  3. 微信开发者工具上传代码 → 设为体验版"
    echo ""
else
    echo "[错误] 服务启动失败，查看日志："
    sudo journalctl -u senbai --no-pager -n 20
    exit 1
fi
