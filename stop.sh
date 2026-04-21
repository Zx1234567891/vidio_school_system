#!/usr/bin/env bash
# 停止 Campus Guard AI 全栈（保留数据卷；加 -v 则清）
set -e
cd "$(dirname "$0")"

echo "[*] docker compose down"
docker compose down

if [[ "$1" == "-v" ]]; then
    echo "[*] 清数据卷..."
    docker volume rm \
        vidio_school_system_postgres_data \
        vidio_school_system_redis_data \
        vidio_school_system_api_data 2>/dev/null || true
fi

echo "[OK] 已停止"
