#!/usr/bin/env python3
"""
Campus Guard AI - 切片导出性能测试
测试异常事件视频切片导出速度
"""

import asyncio
import json
import time
import statistics
import argparse
from datetime import datetime
from typing import Dict, List
import aiohttp


class ClipExportBenchmark:
    """切片导出性能测试"""

    def __init__(self, api_url: str):
        self.api_url = api_url
        self.export_results: List[Dict] = []

    async def create_test_event(self, session: aiohttp.ClientSession) -> str:
        """创建测试事件"""
        event_data = {
            "stream_id": "benchmark_stream",
            "event_type": "fighting",
            "severity": "critical",
            "confidence": 0.95,
            "timestamp": datetime.now().isoformat(),
            "track_ids": ["track_001", "track_002"],
            "participants": [
                {"track_id": "track_001", "role": "aggressor"},
                {"track_id": "track_002", "role": "victim"}
            ]
        }

        async with session.post(
            f"{self.api_url}/api/v1/events",
            json=event_data
        ) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return data["data"]["event_id"]
            else:
                text = await resp.text()
                raise Exception(f"Failed to create event: {text}")

    async def export_clip(self, session: aiohttp.ClientSession, event_id: str,
                         before_sec: int = 5, after_sec: int = 5) -> Dict:
        """导出切片"""
        export_data = {
            "event_id": event_id,
            "stream_id": "benchmark_stream",
            "before_seconds": before_sec,
            "after_seconds": after_sec,
            "format": "mp4"
        }

        start_time = time.time()

        async with session.post(
            f"{self.api_url}/api/v1/clips/export",
            json=export_data
        ) as resp:
            if resp.status == 202:
                data = await resp.json()
                task_id = data["data"]["task_id"]

                # 轮询等待完成
                while True:
                    await asyncio.sleep(0.5)
                    async with session.get(
                        f"{self.api_url}/api/v1/clips/export/{task_id}"
                    ) as status_resp:
                        if status_resp.status == 200:
                            status_data = await status_resp.json()
                            status = status_data["data"]["status"]

                            if status == "completed":
                                elapsed = time.time() - start_time
                                return {
                                    "event_id": event_id,
                                    "task_id": task_id,
                                    "status": "completed",
                                    "elapsed_seconds": elapsed,
                                    "file_size_mb": status_data["data"].get("file_size_mb", 0),
                                    "before_sec": before_sec,
                                    "after_sec": after_sec
                                }
                            elif status == "failed":
                                return {
                                    "event_id": event_id,
                                    "task_id": task_id,
                                    "status": "failed",
                                    "error": status_data["data"].get("error", "unknown")
                                }
            else:
                text = await resp.text()
                return {
                    "event_id": event_id,
                    "status": "failed",
                    "error": text
                }

    async def run_benchmark(self, num_exports: int = 10):
        """运行导出测试"""
        print(f"\n{'='*60}")
        print(f"Campus Guard AI - 切片导出性能测试")
        print(f"{'='*60}")
        print(f"测试次数: {num_exports}")
        print(f"API地址: {self.api_url}")
        print(f"{'='*60}\n")

        async with aiohttp.ClientSession() as session:
            for i in range(num_exports):
                print(f"[{i+1}/{num_exports}] 测试导出...")

                try:
                    # 创建测试事件
                    event_id = await self.create_test_event(session)

                    # 导出切片 (5s before + 5s after = 10s total)
                    result = await self.export_clip(session, event_id, 5, 5)
                    self.export_results.append(result)

                    if result["status"] == "completed":
                        print(f"  ✓ 完成，耗时 {result['elapsed_seconds']:.2f}s, "
                              f"大小 {result.get('file_size_mb', 0):.1f}MB")
                    else:
                        print(f"  ✗ 失败: {result.get('error', 'unknown')}")

                except Exception as e:
                    print(f"  ✗ 异常: {e}")
                    self.export_results.append({
                        "status": "error",
                        "error": str(e)
                    })

                # 间隔1秒
                await asyncio.sleep(1)

        # 分析结果
        self._analyze_results()

    def _analyze_results(self):
        """分析测试结果"""
        print(f"\n{'='*60}")
        print("切片导出测试结果")
        print(f"{'='*60}")

        completed = [r for r in self.export_results if r.get("status") == "completed"]
        failed = [r for r in self.export_results if r.get("status") != "completed"]

        print(f"\n总测试数: {len(self.export_results)}")
        print(f"成功: {len(completed)}")
        print(f"失败: {len(failed)}")

        if completed:
            times = [r["elapsed_seconds"] for r in completed]
            sizes = [r.get("file_size_mb", 0) for r in completed]

            print(f"\n导出耗时统计:")
            print(f"  平均: {statistics.mean(times):.2f}s")
            print(f"  最小: {min(times):.2f}s")
            print(f"  最大: {max(times):.2f}s")
            print(f"  P50: {statistics.median(times):.2f}s")
            print(f"  P95: {sorted(times)[int(len(times)*0.95)]:.2f}s")

            if sizes and any(s > 0 for s in sizes):
                valid_sizes = [s for s in sizes if s > 0]
                if valid_sizes:
                    print(f"\n文件大小统计:")
                    print(f"  平均: {statistics.mean(valid_sizes):.2f}MB")
                    print(f"  最小: {min(valid_sizes):.2f}MB")
                    print(f"  最大: {max(valid_sizes):.2f}MB")

            # 计算吞吐量
            total_duration = sum(times)
            total_size = sum(s for s in sizes if s > 0)
            if total_duration > 0:
                throughput = total_size / total_duration
                print(f"\n平均导出速度: {throughput:.2f} MB/s")

        # 保存详细结果
        result_file = f"benchmark_clip_export_{int(time.time())}.json"
        with open(result_file, "w") as f:
            json.dump({
                "test_type": "clip_export",
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": len(self.export_results),
                    "success": len(completed),
                    "failed": len(failed),
                    "avg_time_seconds": statistics.mean(times) if completed else 0,
                    "p95_time_seconds": sorted(times)[int(len(times)*0.95)] if completed else 0
                },
                "results": self.export_results
            }, f, indent=2)

        print(f"\n详细结果已保存: {result_file}")


def main():
    parser = argparse.ArgumentParser(description="Campus Guard AI 切片导出性能测试")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API 基础URL")
    parser.add_argument("--count", type=int, default=10, help="测试次数 (默认10)")

    args = parser.parse_args()

    benchmark = ClipExportBenchmark(api_url=args.api_url)

    try:
        asyncio.run(benchmark.run_benchmark(num_exports=args.count))
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n测试出错: {e}")
        raise


if __name__ == "__main__":
    main()
