@echo off
REM ============================================================
REM Campus Guard AI - 一键演示
REM   - 确保全栈在跑（如未启动则调用 start.bat）
REM   - 自动创建 11 路流（对应 project1 下 11 类行为视频）
REM   - 打开浏览器
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================
echo  Campus Guard AI - 演示数据推流
echo ========================================

REM --- 1. 检查 api 是否在线；不在就 start ---
curl -sf -o nul http://127.0.0.1:8000/health
if errorlevel 1 (
    echo [*] 全栈未运行，先调用 start.bat...
    call "%~dp0start.bat"
    if errorlevel 1 (
        echo [!] start.bat 失败，终止
        exit /b 1
    )
)

REM --- 2. 等 api 就绪（最多 30s）---
set /a tries=0
:WAIT_API
set /a tries+=1
if %tries% gtr 30 (
    echo [!] api 未就绪
    pause
    exit /b 1
)
curl -sf -o nul http://127.0.0.1:8000/health
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT_API
)

REM --- 3. 创建 11 路流 ---
echo [*] 创建 11 路演示流...
call :CREATE "Kick"        "/project1/Kick/kick_backward_1-1.mp4"
call :CREATE "Laying"      "/project1/Laying/laying_corner_1-1.mp4"
call :CREATE "Phone"       "/project1/Phone/phone_entrance_1-1.mp4"
call :CREATE "Pointing"    "/project1/Pointing/pointing_corner_1-1.mp4"
call :CREATE "Slap face"   "/project1/Slap face/slap_face_corner_1-1.mp4"
call :CREATE "Slap table"  "/project1/Slap table/slap_table_backward_1.mp4"
call :CREATE "Smoking"     "/project1/Smoking/smoking_backward_1-1.mp4"
call :CREATE "Squating"    "/project1/Squating/sqating_concern_1-1.mp4"
call :CREATE "Stand"       "/project1/Stand/stand_backward_1-1.mp4"
call :CREATE "Touch"       "/project1/Touch/touch_corner_1-1.mp4"
call :CREATE "Hit wall"    "/project1/Hit wall/hit_wall_backward_1-1.mp4"

echo.
echo ========================================
echo  演示就绪：http://localhost:3000/streams
echo ========================================
echo.
start "" http://localhost:3000/streams
endlocal
exit /b 0

:CREATE
REM %~1 = name, %~2 = container path
set "PAYLOAD={\"name\":\"%~1\",\"url\":\"%~2\",\"input_type\":\"file\",\"auto_start\":true}"
for /f "delims=" %%r in ('curl -s -o nul -w "%%{http_code}" -X POST http://127.0.0.1:8000/api/v1/streams -H "Content-Type: application/json" -d "!PAYLOAD!"') do set "CODE=%%r"
echo   [!CODE!] %~1
exit /b 0
