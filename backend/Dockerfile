# ===== 森柏后端 Dockerfile（微信云托管）=====
# 基础镜像：Python 3.13 精简版
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 设置时区（定时任务按北京时间执行）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 先复制依赖文件，利用 Docker 缓存层加速构建
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口（微信云托管默认用 80）
EXPOSE 80

# 启动命令：uvicorn 监听 80 端口
# workers=2 适合 0.25~1 核的小规格实例
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--workers", "2"]
