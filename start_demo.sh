#!/bin/bash

echo "=========================================="
echo "Campus Guard AI - 演示模式启动器"
echo "=========================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3"
    exit 1
fi

echo "[*] 检查依赖..."

# 安装依赖
pip3 install fastapi uvicorn websockets -q 2>/dev/null

echo "[*] 依赖检查完成"
echo ""

# 启动演示服务器
echo "[*] 启动演示服务器..."
echo "[*] API地址: http://localhost:8080"
echo "[*] WebSocket: ws://localhost:8080/ws"
echo ""
echo "按Ctrl+C停止服务器"
echo "=========================================="
echo ""

cd "$(dirname "$0")/services/mock-streamer" || exit
python3 demo_server.py
