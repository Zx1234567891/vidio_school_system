"""
Campus Guard AI - 演示模式服务器

一键启动完整演示环境:
1. 模拟推流服务 (使用检测好的视频)
2. FastAPI 控制面 (带演示数据)
3. WebSocket 实时告警推送
"""
import os
import sys
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse

# 导入演示模块
from mock_streamer import get_streamer, init_streamer
from demo_data_generator import DemoDataGenerator
from demo_routes import router as demo_router, init_demo_mode

# 配置
VIDEO_DIR = "D:/vidio_school_system/sucai/output"
API_HOST = "0.0.0.0"
API_PORT = 8888  # 改为8888避免冲突

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


async def alert_publisher():
    """告警发布任务 - 定期推送模拟告警"""
    demo_gen = None

    while True:
        await asyncio.sleep(5)  # 每5秒检查一次

        try:
            # 获取演示数据生成器
            from demo_routes import demo_generator as demo_gen

            if demo_gen and demo_gen.alerts:
                # 随机选择一个未确认告警推送
                unack = [a for a in demo_gen.alerts if not a.acknowledged]
                if unack and len(manager.active_connections) > 0:
                    import random
                    alert = random.choice(unack[:5])
                    await manager.broadcast({
                        "type": "alert",
                        "data": {
                            "id": alert.id,
                            "severity": alert.severity,
                            "title": alert.title,
                            "message": alert.message,
                            "timestamp": alert.timestamp,
                            "stream_name": alert.stream_name
                        }
                    })
        except Exception as e:
            print(f"[!] 告警发布错误: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("=" * 70)
    print("Campus Guard AI - 演示模式")
    print("=" * 70)

    # 检查视频目录
    if not os.path.exists(VIDEO_DIR):
        print(f"[!] 错误: 视频目录不存在: {VIDEO_DIR}")
        yield
        return

    # 初始化演示模式
    print("[*] 初始化演示数据...")
    init_demo_mode(VIDEO_DIR)

    # 启动告警发布任务
    asyncio.create_task(alert_publisher())

    print("[*] 演示服务器已启动")
    print(f"[*] API地址: http://{API_HOST}:{API_PORT}")
    print(f"[*] WebSocket: ws://{API_HOST}:{API_PORT}/ws")
    print("=" * 70)

    yield

    # 关闭时清理
    streamer = get_streamer()
    if streamer:
        streamer.stop_all()
    print("[*] 演示服务器已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="Campus Guard AI - Demo",
    description="校园安防演示服务器 - 使用检测好的视频模拟完整系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册演示路由
app.include_router(demo_router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径 - 显示状态页面"""
    streamer = get_streamer()
    stream_count = len(streamer.streams) if streamer else 0

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Campus Guard AI - Demo</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 12px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                margin: 0 0 10px 0;
            }}
            .status {{
                display: inline-block;
                background: #10b981;
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 14px;
            }}
            .card {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .card h2 {{
                margin-top: 0;
                color: #333;
            }}
            .endpoint {{
                background: #f8f9fa;
                padding: 10px 15px;
                border-radius: 6px;
                margin: 10px 0;
                font-family: monospace;
                font-size: 14px;
            }}
            .method {{
                display: inline-block;
                background: #3b82f6;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 12px;
                margin-right: 10px;
            }}
            .videos {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 10px;
                margin-top: 15px;
            }}
            .video-item {{
                background: #f0f0f0;
                padding: 10px;
                border-radius: 6px;
                font-size: 13px;
            }}
            .video-item .label {{
                color: #666;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Campus Guard AI</h1>
            <p>校园安防视频行为感知与异常事件智能预警系统</p>
            <span class="status">演示模式运行中</span>
        </div>

        <div class="card">
            <h2>系统状态</h2>
            <p>已加载 <strong>{stream_count}</strong> 个检测视频</p>
            <p>API服务: <span style="color: #10b981;">正常</span></p>
            <p>WebSocket服务: <span style="color: #10b981;">正常</span></p>
        </div>

        <div class="card">
            <h2>API端点</h2>
            <div class="endpoint"><span class="method">GET</span> /api/v1/demo/streams - 获取视频流列表</div>
            <div class="endpoint"><span class="method">POST</span> /api/v1/demo/streams/{{id}}/start - 启动推流</div>
            <div class="endpoint"><span class="method">POST</span> /api/v1/demo/streams/{{id}}/stop - 停止推流</div>
            <div class="endpoint"><span class="method">GET</span> /api/v1/demo/events - 获取事件列表</div>
            <div class="endpoint"><span class="method">GET</span> /api/v1/demo/alerts - 获取告警列表</div>
            <div class="endpoint"><span class="method">GET</span> /api/v1/demo/stats - 获取统计数据</div>
            <div class="endpoint"><span class="method">WS</span> /ws - WebSocket实时告警</div>
        </div>

        <div class="card">
            <h2>检测视频列表</h2>
            <div class="videos">
                {''.join([
                    f'<div class="video-item"><div class="label">{s.behavior_label}</div><div>{s.width}x{s.height}@{s.fps:.0f}fps</div></div>'
                    for s in (streamer.streams.values() if streamer else [])
                ])}
            </div>
        </div>

        <div class="card">
            <h2>快速开始</h2>
            <ol>
                <li>确保前端已启动: <code>cd apps/web && npm run dev</code></li>
                <li>访问前端页面查看实时视频和告警</li>
                <li>使用API端点获取数据</li>
            </ol>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """健康检查"""
    streamer = get_streamer()
    return {
        "status": "healthy",
        "mode": "demo",
        "streams_loaded": len(streamer.streams) if streamer else 0,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/streams/{stream_id}/snapshot")
async def stream_snapshot(stream_id: str):
    """单帧快照端点 - 返回当前最新一帧 JPEG，请求完即释放连接，无并发限制"""
    from fastapi.responses import Response, JSONResponse

    streamer = get_streamer()
    if not streamer or stream_id not in streamer.streams:
        return JSONResponse(status_code=404, content={"detail": "流不存在"})

    stream = streamer.streams[stream_id]
    if stream.status != "running":
        streamer.start_stream(stream_id)
        for _ in range(30):
            if streamer.get_latest_frame(stream_id):
                break
            await asyncio.sleep(0.1)

    frame_data = streamer.get_latest_frame(stream_id)
    if not frame_data:
        return JSONResponse(status_code=503, content={"detail": "帧未就绪"})

    return Response(
        content=frame_data,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时告警推送"""
    await manager.connect(websocket)
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "已连接到Campus Guard AI演示服务器",
            "timestamp": datetime.now().isoformat()
        })

        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            elif data.get("type") == "subscribe":
                await websocket.send_json({
                    "type": "subscribed",
                    "channels": data.get("channels", [])
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[!] WebSocket错误: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    print("[*] 启动演示服务器...")
    uvicorn.run(
        "demo_server:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info"
    )
