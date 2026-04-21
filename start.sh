#!/usr/bin/env bash
# ============================================================
# Campus Guard AI - Linux / macOS / WSL 一键启动
# ============================================================
set -e
cd "$(dirname "$0")"

echo "========================================"
echo " Campus Guard AI - 一键启动"
echo "========================================"

# 1. Docker 运行检查
if ! docker info >/dev/null 2>&1; then
    echo "[!] Docker 未运行。请先启动 Docker Desktop / dockerd 后重试。"
    exit 1
fi
echo "[OK] Docker 已运行"

# 2. pytorch 基础镜像预拉（首次 ~5GB）
if ! docker image inspect pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime >/dev/null 2>&1; then
    echo "[*] 首次启动：拉取 pytorch 基础镜像 (~5GB)..."
    if ! docker pull pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime; then
        echo "[!] 拉取失败。请先在 Docker Engine 配置 registry-mirrors（见 README 4.A.0）"
        exit 1
    fi
fi
echo "[OK] pytorch 基础镜像就绪"

# 3. 构建 + 启动
echo "[*] docker compose up -d --build"
docker compose up -d --build

# 4. 等就绪
echo "[*] 等待服务就绪..."
for i in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 \
       && curl -sf http://127.0.0.1:9001/health >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "[!] 服务 2 分钟内未就绪，请查看：docker compose logs -f"
    exit 1
fi

cat <<'EOF'

========================================
 启动完成！
   Web    http://localhost:3000
   API    http://localhost:8000/docs
   AI     http://localhost:9001/models
========================================

查看日志：docker compose logs -f
停止项目：./stop.sh  或  docker compose down

EOF

# 5. 打开浏览器（尽力而为）
URL="http://localhost:3000/streams"
if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open     >/dev/null 2>&1; then open "$URL"      >/dev/null 2>&1 || true
elif command -v cmd.exe  >/dev/null 2>&1; then cmd.exe /c start "$URL" >/dev/null 2>&1 || true
fi
