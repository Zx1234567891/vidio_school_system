#!/usr/bin/env python3
"""
Campus Guard AI - 多路并发压测脚本
测试 20 路视频流并发处理能力
"""

import asyncio
import json
import time
import statistics
import psutil
import argparse
from datetime import datetime
from typing import Dict, List
import aiohttp
import websockets


class MultiStreamBenchmark:
    """多路并发测试"""

    def __init__(self, api_url: str, ws_url: str, num_streams: int = 20):
        self.api_url = api_url
        self.ws_url = ws_url
        self.num_streams = num_streams
        self.results: List[Dict] = []
        self.metrics_history: List[Dict] = []
        self.start_time: float = 0
        self.process = psutil.Process()

    async def create_stream(self, session: aiohttp.ClientSession, idx: int) -> str:
        """创建单个视频流"""
        stream_data = {
            "name": f"benchmark_stream_{idx:03d}",
            "input": {
                "type": "file",
                "url": f"test_video_{(idx % 5) + 1}.mp4"  # 循环使用5个测试视频
            },
            "enabled": True
        }

        async with session.post(
            f"{self.api_url}/api/v1/streams",
            json=stream_data
        ) as resp:
            if resp.status == 201:
                data = await resp.json()
                return data["data"]["id"]
            else:
                text = await resp.text()
                raise Exception(f"Failed to create stream: {text}")

    async def start_stream(self, session: aiohttp.ClientSession, stream_id: str):
        """启动视频流"""
        async with session.post(
            f"{self.api_url}/api/v1/streams/{stream_id}/start"
        ) as resp:
            return resp.status == 200

    async def get_stream_metrics(self, session: aiohttp.ClientSession, stream_id: str) -> Dict:
        """获取流指标"""
        async with session.get(
            f"{self.api_url}/api/v1/streams/{stream_id}"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["data"].get("metrics", {})
            return {}

    async def get_system_metrics(self, session: aiohttp.ClientSession) -> Dict:
        """获取系统指标"""
        async with session.get(
            f"{self.api_url}/api/v1/system/metrics"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["data"]
            return {}

    async def collect_metrics(self, session: aiohttp.ClientSession, duration: int):
        """持续收集指标"""
        start = time.time()
        while time.time() - start < duration:
            try:
                # 系统指标
                sys_metrics = await self.get_system_metrics(session)

                # 进程资源使用
                memory_info = self.process.memory_info()
                cpu_percent = self.process.cpu_percent()

                metric_record = {
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_seconds": time.time() - self.start_time,
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "process_memory_mb": memory_info.rss / 1024 / 1024,
                    "process_cpu_percent": cpu_percent,
                    "active_streams": sys_metrics.get("active_streams", 0),
                    "total_events": sys_metrics.get("total_events_today", 0)
                }

                self.metrics_history.append(metric_record)

                # 每5秒输出一次状态
                if len(self.metrics_history) % 5 == 0:
                    print(f"  [{metric_record['elapsed_seconds']:.0f}s] "
                          f"CPU: {metric_record['cpu_percent']:.1f}% | "
                          f"Mem: {metric_record['memory_percent']:.1f}% | "
                          f"Streams: {metric_record['active_streams']}")

            except Exception as e:
                print(f"  Metrics collection error: {e}")

            await asyncio.sleep(1)

    async def run_benchmark(self, duration: int = 300):
        """运行多路并发测试"""
        print(f"\n{'='*60}")
        print(f"Campus Guard AI - 多路并发压测")
        print(f"{'='*60}")
        print(f"测试路数: {self.num_streams}")
        print(f"测试时长: {duration} 秒")
        print(f"API地址: {self.api_url}")
        print(f"{'='*60}\n")

        self.start_time = time.time()
        stream_ids = []

        async with aiohttp.ClientSession() as session:
            # 1. 创建所有流
            print(f"[1/4] 创建 {self.num_streams} 路视频流...")
            create_start = time.time()

            tasks = [self.create_stream(session, i) for i in range(self.num_streams)]
            try:
                stream_ids = await asyncio.gather(*tasks, return_exceptions=True)
                stream_ids = [sid for sid in stream_ids if not isinstance(sid, Exception)]
                print(f"  ✓ 成功创建 {len(stream_ids)} 路流，耗时 {time.time()-create_start:.2f}s")
            except Exception as e:
                print(f"  ✗ 创建流失败: {e}")
                return

            # 2. 启动所有流
            print(f"\n[2/4] 启动所有视频流...")
            start_tasks = [self.start_stream(session, sid) for sid in stream_ids]
            results = await asyncio.gather(*start_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            print(f"  ✓ 成功启动 {success_count}/{len(stream_ids)} 路流")

            # 3. 预热
            print(f"\n[3/4] 预热 10 秒...")
            await asyncio.sleep(10)

            # 4. 收集指标
            print(f"\n[4/4] 收集性能指标 ({duration} 秒)...")
            await self.collect_metrics(session, duration)

            # 5. 清理
            print(f"\n[清理] 删除测试流...")
            for sid in stream_ids:
                try:
                    await session.delete(f"{self.api_url}/api/v1/streams/{sid}")
                except:
                    pass
            print(f"  ✓ 清理完成")

        # 分析结果
        self._analyze_results()

    def _analyze_results(self):
        """分析测试结果"""
        print(f"\n{'='*60}")
        print("测试结果分析")
        print(f"{'='*60}")

        if not self.metrics_history:
            print("无数据可分析")
            return

        # CPU 统计
        cpu_values = [m["cpu_percent"] for m in self.metrics_history]
        print(f"\n系统 CPU 使用率:")
        print(f"  平均值: {statistics.mean(cpu_values):.1f}%")
        print(f"  P50: {statistics.median(cpu_values):.1f}%")
        print(f"  P95: {sorted(cpu_values)[int(len(cpu_values)*0.95)]:.1f}%")
        print(f"  最大值: {max(cpu_values):.1f}%")

        # 内存统计
        mem_values = [m["memory_percent"] for m in self.metrics_history]
        print(f"\n系统内存使用率:")
        print(f"  平均值: {statistics.mean(mem_values):.1f}%")
        print(f"  P50: {statistics.median(mem_values):.1f}%")
        print(f"  P95: {sorted(mem_values)[int(len(mem_values)*0.95)]:.1f}%")

        # 进程内存
        proc_mem = [m["process_memory_mb"] for m in self.metrics_history]
        print(f"\nAPI 进程内存:")
        print(f"  初始: {proc_mem[0]:.1f} MB")
        print(f"  最终: {proc_mem[-1]:.1f} MB")
        print(f"  峰值: {max(proc_mem):.1f} MB")

        # 保存详细结果
        result_file = f"benchmark_multi_{self.num_streams}streams_{int(time.time())}.json"
        with open(result_file, "w") as f:
            json.dump({
                "test_type": "multi_stream",
                "num_streams": self.num_streams,
                "duration_seconds": len(self.metrics_history),
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "cpu_mean": statistics.mean(cpu_values),
                    "cpu_p50": statistics.median(cpu_values),
                    "cpu_p95": sorted(cpu_values)[int(len(cpu_values)*0.95)],
                    "memory_mean": statistics.mean(mem_values),
                    "process_memory_peak_mb": max(proc_mem)
                },
                "metrics_history": self.metrics_history
            }, f, indent=2)

        print(f"\n详细结果已保存: {result_file}")


def main():
    parser = argparse.ArgumentParser(description="Campus Guard AI 多路并发压测")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API 基础URL")
    parser.add_argument("--ws-url", default="ws://localhost:8000/ws", help="WebSocket URL")
    parser.add_argument("--streams", type=int, default=20, help="并发路数 (默认20)")
    parser.add_argument("--duration", type=int, default=300, help="测试时长秒数 (默认300)")

    args = parser.parse_args()

    benchmark = MultiStreamBenchmark(
        api_url=args.api_url,
        ws_url=args.ws_url,
        num_streams=args.streams
    )

    try:
        asyncio.run(benchmark.run_benchmark(duration=args.duration))
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n测试出错: {e}")
        raise


if __name__ == "__main__":
    main()
