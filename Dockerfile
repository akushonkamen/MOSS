# 使用多阶段构建
# 构建阶段
FROM python:3.10-slim as builder

# 设置工作目录
WORKDIR /app

# 安装Poetry
RUN pip install poetry

# 复制项目文件
COPY pyproject.toml poetry.lock ./

# 导出依赖
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# 运行阶段
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制requirements.txt
COPY --from=builder /app/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 moss && \
    chown -R moss:moss /app

# 切换到非root用户
USER moss

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# 启动命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
