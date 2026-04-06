"""事件发布服务"""

import asyncio
import json
from datetime import datetime
from typing import Optional

from app.services.websocket_manager import WebSocketManager


class EventPublisher:
    """事件发布服务

    负责将事件发布到 WebSocket 和 Redis
    """

    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """启动发布服务"""
        self._running = True
        self._task = asyncio.create_task(self._publish_loop())
        print("[EventPublisher] 启动")

    async def stop(self):
        """停止发布服务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[EventPublisher] 停止")

    async def _publish_loop(self):
        """发布循环"""
        while self._running:
            try:
                # TODO: 从 Redis 或消息队列获取事件
                # 这里暂时发送心跳
                await self._send_heartbeat()
                await asyncio.sleep(30)  # 每30秒发送一次心跳
            except Exception as e:
                print(f"[EventPublisher] 错误: {e}")
                await asyncio.sleep(5)

    async def _send_heartbeat(self):
        """发送心跳"""
        await self.ws_manager.broadcast({
            "type": "heartbeat",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"status": "alive"}
        })

    async def publish_event(self, event_type: str, event_data: dict):
        """发布事件到 WebSocket"""
        message = {
            "type": "event",
            "event_type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }

        # 根据事件类型发布到不同频道
        channel = self._get_channel(event_type)
        await self.ws_manager.publish_to_channel(channel, message)

    def _get_channel(self, event_type: str) -> str:
        """根据事件类型获取频道"""
        channel_map = {
            "stream_connected": "streams",
            "stream_disconnected": "streams",
            "stream_error": "streams",
            "alert": "alerts",
            "event_detected": "events",
            "metrics_update": "metrics",
        }
        return channel_map.get(event_type, "all")

    async def publish_alert(self, alert_data: dict):
        """发布告警"""
        await self.publish_event("alert", alert_data)

    async def publish_stream_status(self, stream_id: str, status: str, details: dict = None):
        """发布流状态变更"""
        await self.publish_event("stream_status_change", {
            "stream_id": stream_id,
            "status": status,
            "details": details or {}
        })

    async def publish_metrics(self, metrics_data: dict):
        """发布指标更新"""
        await self.publish_event("metrics_update", metrics_data)
