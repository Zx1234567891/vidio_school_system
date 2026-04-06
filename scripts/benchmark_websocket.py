#!/usr/bin/env python3
"""
Campus Guard AI - WebSocket 实时推送延迟测试
测试告警从生成到推送到前端的延迟
"""

import asyncio
import json
import time
import statistics
import argparse
from datetime import datetime
from typing import Dict, List
import aiohttp
import websockets


class WebSocketLatencyBenchmark:
    """WebSocket 延迟测试"""

    def __init__(self, api_url: str, ws_url: str):
        self.api_url = api_url
        self.ws_url = ws_url
        self.latencies: List[float] = []
        self.received_messages: List[Dict] = []
        self.expected_events: int = 0
        self.received_events: int = 0

    async def websocket_listener(self):
        """WebSocket 监听器"""
        try:
            async with websockets.connect(self.ws_url) as ws:
                # 订阅告警频道
                await ws.send(json.dumps({
                    "type": "subscribe",
                    "channels": ["alerts"]
                }))

                # 监听消息
                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        data = json.loads(message)

                        receive_time = time.time()

                        if data.get("type") == "alert":
                            payload = data.get("payload", {})
                            event_timestamp = payload.get("timestamp")

                            if event_timestamp:
                                # 计算延迟
                                try:
                                    event_time = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                                    event_ts = event_time.timestamp()
                                    latency_ms = (receive_time - event_ts) * 1000

                                    self.latencies.append(latency_ms)
                                    self.received_events += 1

                                    self.received_messages.append({
                                        "event_id": payload.get("event_id"),
                                        "latency_ms": latency_ms,
                                        "receive_time": datetime.now().isoformat()
                                    })
                                except:
                                    pass

                    except asyncio.TimeoutError:
                        break

        except Exception as e:
            print(f"  WebSocket error: {e}")

    async def create_test_alert(self, session: aiohttp.ClientSession) -> str:
        """创建测试告警"""
        event_data = {
            "stream_id": "benchmark_stream",
            "event_type": "fighting",
            "severity": "critical",
            "confidence": 0.95,
            "timestamp": datetime.now().isoformat(),
            "track_ids": ["track_001"],
            "participants": [{"track_id": "track_001", "role": "aggressor"}]
        }

        async with session.post(
            f"{self.api_url}/api/v1/events",
            json=event_data
        ) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return data["data"].get("event_id", "")
        return ""

    async def run_benchmark(self, num_alerts: int = 50, interval: float = 1.0):
        """运行延迟测试"""
        print(f"\n{'='*60}")
        print(f"Campus Guard AI - WebSocket 延迟测试")
        print(f"{'='*60}")
        print(f"测试告警数: {num_alerts}")
        print(f"发送间隔: {interval}s")
        print(f"API地址: {self.api_url}")
        print(f"WebSocket: {self.ws_url}")
        print(f"{'='*60}\n")

        self.expected_events = num_alerts

        # 启动 WebSocket 监听器
        ws_task = asyncio.create_task(self.websocket_listener())

        # 等待连接建立
        await asyncio.sleep(1)

        async with aiohttp.ClientSession() as session:
            for i in range(num_alerts):
                print(f"[{i+1}/{num_alerts}] 发送测试告警...", end=" ")

                try:
                    event_id = await self.create_test_alert(session)
                    if event_id:
                        print(f"event_id={event_id[:8]}...")
                    else:
                        print("(no event_id)")
                except Exception as e:
                    print(f"失败: {e}")

                await asyncio.sleep(interval)

        # 等待接收所有消息
        print(f"\n等待接收消息...")
        await asyncio.sleep(5)

        # 取消 WebSocket 任务
        ws_task.cancel()
        try:
            await ws_task
        except asyncio.CancelledError:
            pass

        # 分析结果
        self._analyze_results()

    def _analyze_results(self):
        """分析延迟结果"""
        print(f"\n{'='*60}")
        print("WebSocket 延迟测试结果")
        print(f"{'='*60}")

        print(f"\n消息统计:")
        print(f"  预期接收: {self.expected_events}")
        print(f"  实际接收: {self.received_events}")
        print(f"  接收率: {self.received_events/self.expected_events*100:.1f}%" if self.expected_events > 0 else "  接收率: N/A")

        if self.latencies:
            print(f"\n端到端延迟统计:")
            print(f"  样本数: {len(self.latencies)}")
            print(f"  平均值: {statistics.mean(self.latencies):.2f} ms")
            print(f"  最小值: {min(self.latencies):.2f} ms")
            print(f"  最大值: {max(self.latencies):.2f} ms")
            print(f"  P50: {statistics.median(self.latencies):.2f} ms")

            sorted_latencies = sorted(self.latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)

            print(f"  P95: {sorted_latencies[p95_idx]:.2f} ms")
            print(f"  P99: {sorted_latencies[p99_idx]:.2f} ms")

            # 延迟分布
            print(f"\n延迟分布:")
            ranges = [(0, 50), (50, 100), (100, 200), (200, 500), (500, float('inf'))]
            for low, high in ranges:
                count = sum(1 for l in self.latencies if low <= l < high)
                pct = count / len(self.latencies) * 100
                high_str = f"{high}" if high != float('inf') else "+"
                print(f"  {low}-{high_str}ms: {count} ({pct:.1f}%)")

        # 保存详细结果
        result_file = f"benchmark_websocket_{int(time.time())}.json"
        with open(result_file, "w") as f:
            json.dump({
                "test_type": "websocket_latency",
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "expected": self.expected_events,
                    "received": self.received_events,
                    "receive_rate": self.received_events/self.expected_events*100 if self.expected_events > 0 else 0,
                    "avg_latency_ms": statistics.mean(self.latencies) if self.latencies else 0,
                    "p95_latency_ms": sorted(self.latencies)[int(len(self.latencies)*0.95)] if self.latencies else 0,
                    "p99_latency_ms": sorted(self.latencies)[int(len(self.latencies)*0.99)] if self.latencies else 0
                },
                "latencies": self.latencies,
                "messages": self.received_messages
            }, f, indent=2)

        print(f"\n详细结果已保存: {result_file}")


def main():
    parser = argparse.ArgumentParser(description="Campus Guard AI WebSocket 延迟测试")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API 基础URL")
    parser.add_argument("--ws-url", default="ws://localhost:8000/ws", help="WebSocket URL")
    parser.add_argument("--count", type=int, default=50, help="测试告警数 (默认50)")
    parser.add_argument("--interval", type=float, default=1.0, help="发送间隔秒数 (默认1.0)")

    args = parser.parse_args()

    benchmark = WebSocketLatencyBenchmark(
        api_url=args.api_url,
        ws_url=args.ws_url
    )

    try:
        asyncio.run(benchmark.run_benchmark(num_alerts=args.count, interval=args.interval))
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n测试出错: {e}")
        raise


if __name__ == "__main__":
    main()
