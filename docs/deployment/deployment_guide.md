# MOSS 部署指南

## 目录
1. [系统要求](#系统要求)
2. [开发环境部署](#开发环境部署)
3. [生产环境部署](#生产环境部署)
4. [Docker部署](#docker部署)
5. [Kubernetes部署](#kubernetes部署)
6. [监控配置](#监控配置)
7. [备份策略](#备份策略)
8. [故障恢复](#故障恢复)

## 系统要求

### 硬件要求
- CPU: 8核心或更多
- 内存: 16GB或更多
- 存储: 100GB SSD
- GPU: NVIDIA GPU (推荐用于模型推理)

### 软件要求
- 操作系统: Ubuntu 20.04 LTS或更高版本
- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Docker 20.10+
- NVIDIA Driver 470+（如使用GPU）
- CUDA 11.7+（如使用GPU）

## 开发环境部署

### 1. 安装依赖

```bash
# 安装系统依赖
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip postgresql redis-server

# 安装Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安装项目依赖
poetry install
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

### 3. 初始化数据库

```bash
# 创建数据库
sudo -u postgres psql -c "CREATE DATABASE moss;"
sudo -u postgres psql -c "CREATE USER moss WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE moss TO moss;"

# 运行数据库迁移
poetry run alembic upgrade head
```

### 4. 启动开发服务器

```bash
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 生产环境部署

### 1. 系统准备

```bash
# 创建服务用户
sudo useradd -r -s /bin/false moss

# 创建应用目录
sudo mkdir -p /opt/moss
sudo chown moss:moss /opt/moss

# 配置系统限制
sudo nano /etc/security/limits.conf
# 添加以下行
moss soft nofile 65535
moss hard nofile 65535
```

### 2. 安装依赖

```bash
# 安装系统依赖
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip postgresql redis-server nginx supervisor

# 配置虚拟环境
python3.10 -m venv /opt/moss/venv
source /opt/moss/venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置Supervisor

```ini
# /etc/supervisor/conf.d/moss.conf
[program:moss]
command=/opt/moss/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/opt/moss
user=moss
autostart=true
autorestart=true
stderr_logfile=/var/log/moss/err.log
stdout_logfile=/var/log/moss/out.log
environment=
    PYTHONPATH="/opt/moss",
    DATABASE_URL="postgresql://moss:password@localhost/moss"

[program:moss-worker]
command=/opt/moss/venv/bin/celery -A src.worker worker --loglevel=info
directory=/opt/moss
user=moss
autostart=true
autorestart=true
stderr_logfile=/var/log/moss/celery-err.log
stdout_logfile=/var/log/moss/celery-out.log
```

### 4. 配置Nginx

```nginx
# /etc/nginx/sites-available/moss
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /static {
        alias /opt/moss/static;
    }

    location /media {
        alias /opt/moss/media;
    }
}
```

### 5. SSL配置

```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d your_domain.com
```

## Docker部署

### 1. 构建镜像

```bash
# 构建应用镜像
docker build -t moss:latest .

# 启动服务
docker-compose up -d
```

### 2. Docker Compose配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    image: moss:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://moss:password@db/moss
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=moss
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=moss
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Kubernetes部署

### 1. 准备Kubernetes配置

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: moss
spec:
  replicas: 3
  selector:
    matchLabels:
      app: moss
  template:
    metadata:
      labels:
        app: moss
    spec:
      containers:
      - name: moss
        image: moss:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: moss-secrets
              key: database-url
```

### 2. 部署到Kubernetes

```bash
# 创建命名空间
kubectl create namespace moss

# 应用配置
kubectl apply -f kubernetes/

# 检查部署状态
kubectl get pods -n moss
```

## 监控配置

### 1. Prometheus配置

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'moss'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
```

### 2. Grafana仪表板

- 导入预配置的仪表板
- 配置告警规则
- 设置通知渠道

## 备份策略

### 1. 数据库备份

```bash
# 创建备份脚本
#!/bin/bash
BACKUP_DIR="/backup/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
pg_dump -U moss moss > "$BACKUP_DIR/moss_$TIMESTAMP.sql"
```

### 2. 文件备份

```bash
# 备份应用数据
rsync -avz /opt/moss/media /backup/moss/
```

## 故障恢复

### 1. 数据库恢复

```bash
# 从备份恢复数据库
psql -U moss moss < backup.sql
```

### 2. 应用恢复

```bash
# 回滚部署
kubectl rollout undo deployment/moss

# 检查日志
kubectl logs -f deployment/moss
```

## 性能优化

### 1. 数据库优化

```sql
-- 添加索引
CREATE INDEX idx_device_status ON devices(status);

-- 优化查询
VACUUM ANALYZE devices;
```

### 2. 缓存配置

```python
# 配置Redis缓存
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## 安全配置

### 1. 防火墙配置

```bash
# 配置UFW
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. 安全头部配置

```nginx
# Nginx安全头部
add_header X-Frame-Options "SAMEORIGIN";
add_header X-XSS-Protection "1; mode=block";
add_header X-Content-Type-Options "nosniff";
```

## 维护指南

### 1. 日常维护

```bash
# 检查服务状态
systemctl status moss

# 检查日志
tail -f /var/log/moss/app.log

# 清理旧日志
find /var/log/moss -name "*.log.*" -mtime +30 -delete
```

### 2. 更新流程

```bash
# 更新应用
cd /opt/moss
git pull
poetry install
alembic upgrade head
sudo supervisorctl restart moss
``` 