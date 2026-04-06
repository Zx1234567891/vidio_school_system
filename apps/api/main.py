"""
Campus Guard AI - FastAPI 控制面

提供 REST API 和 WebSocket 实时推送
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from app.routers import (
    health_router, streams_router, events_router,
    reviews_router, clips_router, training_router,
    metrics_router, system_router
)
from app.core.config import settings
from app.core.database import init_db
from app.services.websocket_manager import WebSocketManager
from app.services.event_publisher import EventPublisher

# WebSocket 管理器
ws_manager = WebSocketManager()
event_publisher = EventPublisher(ws_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    await init_db()

    # 启动事件发布器
    asyncio.create_task(event_publisher.start())

    print(f"🚀 Campus Guard API 启动 - 环境: {settings.ENV}")
    print(f"📡 WebSocket 服务已启动")
    print(f"🤖 AI Runtime 集成已启用")
    yield

    # 关闭时清理
    await event_publisher.stop()
    print("👋 Campus Guard API 关闭")


app = FastAPI(
    title="Campus Guard AI API",
    description="校园安防视频行为感知系统控制面 - 支持多路视频流、实时行为识别、异常预警",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, tags=["Health"])
app.include_router(streams_router, prefix="/api/v1/streams", tags=["Streams"])
app.include_router(events_router, prefix="/api/v1/events", tags=["Events"])
app.include_router(reviews_router, prefix="/api/v1/reviews", tags=["Reviews"])
app.include_router(clips_router, prefix="/api/v1/clips", tags=["Clips"])
app.include_router(training_router, prefix="/api/v1/training", tags=["Training"])
app.include_router(metrics_router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(system_router, prefix="/api/v1/system", tags=["System"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时告警推送"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息（心跳或订阅请求）
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": data.get("timestamp")})
            elif data.get("type") == "subscribe":
                # 订阅特定流或事件类型
                channels = data.get("channels", [])
                ws_manager.subscribe(websocket, channels)
                await websocket.send_json({"type": "subscribed", "channels": channels})
            else:
                await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
