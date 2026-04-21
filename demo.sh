#!/usr/bin/env bash
# ============================================================
# Campus Guard AI - 一键演示（Linux / macOS / WSL）
#   - 确保全栈在跑（如未启动则调用 start.sh）
#   - 自动为 project1 下 11 类视频各创建一路流
#   - 打开浏览器
# ============================================================
set -e
cd "$(dirname "$0")"

echo "========================================"
echo " Campus Guard AI - 演示数据推流"
echo "========================================"

# 1. api 在线则跳过；否则走 start
if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "[*] 全栈未运行，先调用 start.sh..."
    ./start.sh
fi

# 2. 等 api 就绪
for i in $(seq 1 30); do
    curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break
    sleep 1
done

create_stream() {
    local name="$1"
    local url="$2"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST http://127.0.0.1:8000/api/v1/streams \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"$name\",\"url\":\"$url\",\"input_type\":\"file\",\"auto_start\":true}")
    echo "  [$code] $name"
}

echo "[*] 创建 11 路演示流..."
create_stream "Kick"       "/project1/Kick/kick_backward_1-1.mp4"
create_stream "Laying"     "/project1/Laying/laying_corner_1-1.mp4"
create_stream "Phone"      "/project1/Phone/phone_entrance_1-1.mp4"
create_stream "Pointing"   "/project1/Pointing/pointing_corner_1-1.mp4"
create_stream "Slap face"  "/project1/Slap face/slap_face_corner_1-1.mp4"
create_stream "Slap table" "/project1/Slap table/slap_table_backward_1.mp4"
create_stream "Smoking"    "/project1/Smoking/smoking_backward_1-1.mp4"
create_stream "Squating"   "/project1/Squating/sqating_concern_1-1.mp4"
create_stream "Stand"      "/project1/Stand/stand_backward_1-1.mp4"
create_stream "Touch"      "/project1/Touch/touch_corner_1-1.mp4"
create_stream "Hit wall"   "/project1/Hit wall/hit_wall_backward_1-1.mp4"

cat <<'EOF'

========================================
 演示就绪：http://localhost:3000/streams
========================================

EOF

URL="http://localhost:3000/streams"
if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open     >/dev/null 2>&1; then open "$URL"     >/dev/null 2>&1 || true
elif command -v cmd.exe  >/dev/null 2>&1; then cmd.exe /c start "$URL" >/dev/null 2>&1 || true
fi
