@echo off
chcp 65001 >nul
echo ==========================================
echo Campus Guard AI - 演示模式启动器
echo ==========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

echo [*] 检查依赖...

REM 检查并安装依赖
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [*] 安装FastAPI...
    pip install fastapi uvicorn websockets -q
)

echo [*] 依赖检查完成
echo.

REM 启动演示服务器
echo [*] 启动演示服务器...
echo [*] API地址: http://localhost:8080
echo [*] WebSocket: ws://localhost:8080/ws
echo.
echo 按Ctrl+C停止服务器
echo ==========================================
echo.

cd /d "D:\vidio_school_system\services\mock-streamer"
python demo_server.py

pause
