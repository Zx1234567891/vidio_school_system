@echo off
REM ============================================================
REM Campus Guard AI - Windows 一键启动
REM   - 启动 Docker 全栈（postgres + redis + ai-runtime + api + web）
REM   - 等就绪后打开浏览器
REM 用法：双击 start.bat，或在 cmd 里执行
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================
echo  Campus Guard AI - 一键启动
echo ========================================

REM --- 1. 检查 Docker ---
docker info >nul 2>&1
if errorlevel 1 (
    echo [!] Docker Desktop 未运行。请先启动 Docker Desktop 后重试。
    pause
    exit /b 1
)
echo [OK] Docker 已运行

REM --- 2. 检查基础镜像 pytorch（首次启动需预拉 ~5GB） ---
docker image inspect pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime >nul 2>&1
if errorlevel 1 (
    echo [*] 首次启动：拉取 pytorch 基础镜像 ^(~5GB，走 Docker Hub 镜像^)...
    docker pull pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime
    if errorlevel 1 (
        echo [!] 拉取失败。请确认 Docker Engine settings 里已配置 registry-mirrors
        echo     ^(见 README 4.A.0^)，重试后再运行本脚本。
        pause
        exit /b 1
    )
)
echo [OK] pytorch 基础镜像就绪

REM --- 3. 构建 + 启动 ---
echo [*] docker compose up -d --build
docker compose up -d --build
if errorlevel 1 (
    echo [!] 启动失败，见上方日志
    pause
    exit /b 1
)

REM --- 4. 等 api / ai-runtime 就绪 ---
echo [*] 等待服务就绪...
set /a tries=0
:WAIT
set /a tries+=1
if %tries% gtr 60 (
    echo [!] 服务 60 秒内未就绪，请查看日志：docker compose logs -f
    pause
    exit /b 1
)
curl -sf -o nul http://127.0.0.1:8000/health
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto WAIT
)
curl -sf -o nul http://127.0.0.1:9001/health
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto WAIT
)

echo.
echo ========================================
echo  启动完成！
echo    Web    http://localhost:3000
echo    API    http://localhost:8000/docs
echo    AI     http://localhost:9001/models
echo ========================================
echo.
echo 查看日志：docker compose logs -f
echo 停止项目：stop.bat  或  docker compose down
echo.

REM --- 5. 打开浏览器 ---
start "" http://localhost:3000/streams

endlocal
