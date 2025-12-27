# 使用轻量级但兼容性更好的 Python Slim 镜像
FROM python:3.9-slim

# 设置时区为 GMT+8
# 安装 tzdata 和 ca-certificates (curl_cffi 可能需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有 .py 文件到工作目录
COPY *.py ./

# 设置默认启动命令
CMD ["python", "scheduler.py"]