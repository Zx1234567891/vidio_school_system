# Campus Guard AI - 部署说明

## 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Docker Host                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   web       │  │    api      │  │   stream-core       │  │
│  │  (Next.js)  │  │  (FastAPI)  │  │   (C++20)           │  │
│  │  :3000      │  │   :8000     │  │   :9000             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                │                  │                │
│         └────────────────┼──────────────────┘                │
│                          │                                   │
│  ┌─────────────┐  ┌──────┴──────┐  ┌─────────────────────┐  │
│  │  postgres   │  │    redis    │  │   nginx (可选)      │  │
│  │   :5432     │  │   :6379     │  │   :80/:443          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 环境要求

### 最低配置

| 组件 | 配置 |
|------|------|
| CPU | 8核16线程 |
| 内存 | 16GB |
| 存储 | 100GB SSD |
| GPU | 可选 (加速推理) |
| 网络 | 千兆以太网 |

### 推荐配置 (20路并发)

| 组件 | 配置 |
|------|------|
| CPU | 16核32线程 |
| 内存 | 32GB |
| 存储 | 500GB NVMe SSD |
| GPU | NVIDIA RTX 4060 或更高 |
| 网络 | 千兆以太网 |

## 部署方式

### 方式一：Docker Compose (推荐)

#### 1. 准备环境

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. 克隆项目

```bash
git clone <repo-url>
cd campus-guard
```

#### 3. 配置环境变量

```bash
cp .env.example .env

# 编辑 .env 文件
vim .env
```

`.env` 示例：

```bash
# 数据库
POSTGRES_USER=campus_guard
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=campus_guard

# Redis
REDIS_PASSWORD=your_redis_password

# API
API_SECRET_KEY=your_secret_key_here
API_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Stream Core
STREAM_CORE_MAX_STREAMS=20
STREAM_CORE_THREAD_POOL_SIZE=8

# 存储路径
DATA_DIR=/data/campus-guard
CLIPS_DIR=/data/campus-guard/clips
```

#### 4. 启动服务

```bash
# 创建数据目录
mkdir -p /data/campus-guard/clips

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps
```

#### 5. 初始化数据库

```bash
# 进入 API 容器
docker-compose exec api bash

# 运行数据库迁移
python -c "from app.core.database import init_db; init_db()"

# 退出
exit
```

#### 6. 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 访问前端
open http://localhost:3000
```

### 方式二：手动部署

#### 1. 安装依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    python3-pip \
    nodejs \
    npm \
    postgresql \
    redis-server

# Python 依赖
pip3 install -r apps/api/requirements.txt
pip3 install -r services/ai-runtime/requirements.txt

# Node.js 依赖
cd apps/web && npm install
```

#### 2. 配置数据库

```bash
# 启动 PostgreSQL
sudo systemctl start postgresql

# 创建数据库
sudo -u postgres psql -c "CREATE USER campus_guard WITH PASSWORD 'password';"
sudo -u postgres psql -c "CREATE DATABASE campus_guard OWNER campus_guard;"

# 启动 Redis
sudo systemctl start redis-server
```

#### 3. 构建 Stream Core

```bash
cd services/stream-core
mkdir -p build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

#### 4. 启动服务

```bash
# 终端1: 启动 API
cd apps/api
uvicorn main:app --host 0.0.0.0 --port 8000

# 终端2: 启动前端
cd apps/web
npm run build
npm start

# 终端3: 启动 Stream Core (可选)
./services/stream-core/build/stream_core_app
```

## 生产环境优化

### 1. Nginx 反向代理

```nginx
# /etc/nginx/sites-available/campus-guard
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. Systemd 服务

```ini
# /etc/systemd/system/campus-guard-api.service
[Unit]
Description=Campus Guard API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=campus-guard
WorkingDirectory=/opt/campus-guard/apps/api
Environment=PATH=/opt/campus-guard/venv/bin
EnvironmentFile=/opt/campus-guard/.env
ExecStart=/opt/campus-guard/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl enable campus-guard-api
sudo systemctl start campus-guard-api
```

### 3. 日志轮转

```bash
# /etc/logrotate.d/campus-guard
/opt/campus-guard/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 campus-guard campus-guard
}
```

### 4. 监控

```bash
# 安装 Prometheus Node Exporter
# 配置 Grafana 监控面板
# 监控指标：CPU、内存、磁盘、网络、应用指标
```

## 备份与恢复

### 数据库备份

```bash
# 自动备份脚本
#!/bin/bash
BACKUP_DIR="/backup/campus-guard"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL 备份
docker-compose exec -T postgres pg_dump -U campus_guard campus_guard > "$BACKUP_DIR/db_$DATE.sql"

# 保留最近30天备份
find $BACKUP_DIR -name "db_*.sql" -mtime +30 -delete
```

### 数据恢复

```bash
# 恢复数据库
docker-compose exec -T postgres psql -U campus_guard campus_guard < backup_file.sql
```

## 故障排查

### 常见问题

#### 1. 服务无法启动

```bash
# 检查日志
docker-compose logs api
docker-compose logs web

# 检查端口占用
sudo netstat -tlnp | grep 8000
sudo netstat -tlnp | grep 3000
```

#### 2. 数据库连接失败

```bash
# 检查 PostgreSQL 状态
docker-compose exec postgres pg_isready

# 检查连接配置
cat apps/api/.env | grep DATABASE
```

#### 3. 视频流无法接入

```bash
# 检查 FFmpeg 安装
ffmpeg -version

# 检查 Stream Core 日志
docker-compose logs stream-core

# 测试 RTSP 流
ffplay rtsp://your-camera-url
```

#### 4. 性能问题

```bash
# 运行性能测试
cd scripts
python benchmark_all.py

# 监控资源使用
htop
docker stats
```

## 安全建议

1. **修改默认密码**: 所有服务的默认密码必须修改
2. **防火墙配置**: 只开放必要的端口 (80, 443)
3. **HTTPS**: 生产环境必须使用 HTTPS
4. **定期更新**: 及时更新依赖库和系统补丁
5. **访问控制**: 配置 API 访问频率限制

## 升级指南

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 拉取最新代码
git pull origin main

# 3. 更新依赖
docker-compose build --no-cache

# 4. 重启服务
docker-compose down
docker-compose up -d

# 5. 验证升级
curl http://localhost:8000/health
```

## 支持

- 文档: [docs/](./)
- 问题反馈: [GitHub Issues]
- 邮件支持: [support@example.com]
