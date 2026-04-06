"""WebSocket 连接管理器"""

from typing import List, Dict, Set
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 所有活跃连接
        self.active_connections: List[WebSocket] = []
        # 订阅映射: connection -> set of channels
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        # 锁
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
            self.subscriptions[websocket] = set()
        print(f"[WebSocket] 新连接，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        print(f"[WebSocket] 连接断开，当前连接数: {len(self.active_connections)}")

    def subscribe(self, websocket: WebSocket, channels: List[str]):
        """订阅频道"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(channels)

    def unsubscribe(self, websocket: WebSocket, channels: List[str]):
        """取消订阅"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].difference_update(channels)

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WebSocket] 发送失败: {e}")
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    async def publish_to_channel(self, channel: str, message: dict):
        """发布消息到指定频道"""
        message["channel"] = channel
        message["timestamp"] = datetime.utcnow().isoformat()

        disconnected = []
        for connection in self.active_connections:
            # 检查订阅
            subscribed_channels = self.subscriptions.get(connection, set())
            if channel in subscribed_channels or "all" in subscribed_channels:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"[WebSocket] 发送失败: {e}")
                    disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"[WebSocket] 发送失败: {e}")
            self.disconnect(websocket)


# 全局 WebSocket 管理器实例
websocket_manager = WebSocketManager()
