@echo off
REM 停止 Campus Guard AI 全栈（保留数据卷；加 -v 则清）
cd /d "%~dp0"
echo [*] docker compose down
docker compose down
if "%1"=="-v" (
    echo [*] docker volume prune（会清 postgres/redis/sqlite 数据）
    docker volume rm vidio_school_system_postgres_data vidio_school_system_redis_data vidio_school_system_api_data 2>nul
)
echo [OK] 已停止
