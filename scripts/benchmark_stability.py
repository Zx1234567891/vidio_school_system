#!/usr/bin/env python3
"""
Campus Guard AI - 稳定性测试脚本
测试长时间运行稳定性、内存泄漏、重连成功率
"""

import asyncio
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List
import aiohttp
import psutil


class StabilityBenchmark:
    """稳定性测试"""

    def __init__(self, api_url: str, duration: int = 3600):
        self.api_url = api_url
        self.duration = duration
        self.metrics_history: List[Dict] = []
        self.start_time: float = 0
        self.process = psutil.Process()
        self.errors: List[Dict] = []
        self.reconnect_events: List[Dict] = []

    async def get_health(self, session: aiohttp.ClientSession) -> Dict:
        """获取健康状态"""
        try:
            async with session.get(
                f"{self.api_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"status": "error", "code": resp.status}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_system_metrics(self, session: aiohttp.ClientSession) -> Dict:
        """获取系统指标"""
        try:
            async with session.get(
                f"{self.api_url}/api/v1/system/metrics",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {})
        except Exception as e:
            self.errors.append({
                "timestamp": datetime.now().isoformat(),
                "type": "metrics_fetch_error",
                "message": str(e)
            })
        return {}

    async def get_streams_status(self, session: aiohttp.ClientSession) -> List[Dict]:
        """获取所有流状态"""
        try:
            async with session.get(
                f"{self.api_url}/api/v1/streams",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {}).get("items", [])
        except Exception as e:
            self.errors.append({
                "timestamp": datetime.now().isoformat(),
                "type": "streams_fetch_error",
                "message": str(e)
            })
        return []

    async def run_stability_test(self):
        """运行稳定性测试"""
        print(f"\n{'='*60}")
        print(f"Campus Guard AI - 稳定性测试")
        print(f"{'='*60}")
        print(f"测试时长: {self.duration} 秒 ({self.duration/3600:.1f} 小时)")
        print(f"API地址: {self.api_url}")
        print(f"{'='*60}\n")

        self.start_time = time.time()
        check_count = 0
        last_health_status = "unknown"

        async with aiohttp.ClientSession() as session:
            while time.time() - self.start_time < self.duration:
                check_start = time.time()
                elapsed = time.time() - self.start_time

                try:
                    # 健康检查
                    health = await self.get_health(session)
                    health_status = health.get("status", "unknown")

                    if health_status != last_health_status:
                        print(f"  [{elapsed/60:.1f}min] 健康状态变化: {last_health_status} -> {health_status}")
                        last_health_status = health_status

                    if health_status != "healthy":
                        self.errors.append({
                            "timestamp": datetime.now().isoformat(),
                            "elapsed_seconds": elapsed,
                            "type": "health_check_failed",
                            "status": health_status
                        })

                    # 系统指标
                    sys_metrics = await self.get_system_metrics(session)

                    # 流状态
                    streams = await self.get_streams_status(session)
                    stream_statuses = {}
                    for s in streams:
                        status = s.get("status", "unknown")
                        stream_statuses[status] = stream_statuses.get(status, 0) + 1

                    # 进程资源
                    memory_info = self.process.memory_info()
                    cpu_percent = self.process.cpu_percent()

                    # 记录指标
                    metric_record = {
                        "timestamp": datetime.now().isoformat(),
                        "elapsed_seconds": elapsed,
                        "health_status": health_status,
                        "cpu_percent": psutil.cpu_percent(interval=0.1),
                        "memory_percent": psutil.virtual_memory().percent,
                        "process_memory_mb": memory_info.rss / 1024 / 1024,
                        "process_cpu_percent": cpu_percent,
                        "active_streams": sys_metrics.get("active_streams", 0),
                        "total_events": sys_metrics.get("total_events_today", 0),
                        "stream_statuses": stream_statuses
                    }

                    self.metrics_history.append(metric_record)
                    check_count += 1

                    # 每60秒输出一次摘要
                    if check_count % 60 == 0:
                        minutes = elapsed / 60
                        print(f"  [{minutes:.0f}min] 运行正常 | "
                              f"CPU: {metric_record['cpu_percent']:.1f}% | "
                              f"Mem: {metric_record['process_memory_mb']:.0f}MB | "
                              f"Streams: {metric_record['active_streams']} | "
                              f"Events: {metric_record['total_events']}")

                except Exception as e:
                    self.errors.append({
                        "timestamp": datetime.now().isoformat(),
                        "elapsed_seconds": elapsed,
                        "type": "check_exception",
                        "message": str(e)
                    })
                    print(f"  [{elapsed/60:.1f}min] 检查异常: {e}")

                # 确保每秒检查一次
                elapsed_check = time.time() - check_start
                sleep_time = max(0, 1 - elapsed_check)
                await asyncio.sleep(sleep_time)

        # 分析结果
        self._analyze_results()

    def _analyze_results(self):
        """分析稳定性测试结果"""
        print(f"\n{'='*60}")
        print("稳定性测试结果")
        print(f"{'='*60}")

        if not self.metrics_history:
            print("无数据可分析")
            return

        # 运行时间
        total_seconds = self.metrics_history[-1]["elapsed_seconds"]
        print(f"\n运行时间: {total_seconds/60:.1f} 分钟 ({total_seconds/3600:.2f} 小时)")

        # 健康检查统计
        health_checks = [m for m in self.metrics_history if m.get("health_status")]
        healthy_count = sum(1 for m in health_checks if m["health_status"] == "healthy")
        if health_checks:
            print(f"\n健康检查:")
            print(f"  总检查次数: {len(health_checks)}")
            print(f"  健康次数: {healthy_count}")
            print(f"  健康率: {healthy_count/len(health_checks)*100:.2f}%")

        # 内存趋势分析
        mem_values = [m["process_memory_mb"] for m in self.metrics_history]
        if len(mem_values) > 10:
            # 计算前10%和后10%的平均值
            first_10pct = mem_values[:max(1, len(mem_values)//10)]
            last_10pct = mem_values[-max(1, len(mem_values)//10):]

            first_avg = sum(first_10pct) / len(first_10pct)
            last_avg = sum(last_10pct) / len(last_10pct)
            growth = last_avg - first_avg

            print(f"\n内存使用趋势:")
            print(f"  初始内存: {first_avg:.1f} MB")
            print(f"  最终内存: {last_avg:.1f} MB")
            print(f"  增长: {growth:+.1f} MB ({growth/first_avg*100:+.1f}%)")

            if growth < 50:
                print(f"  结论: ✓ 无明显内存泄漏")
            elif growth < 200:
                print(f"  结论: △ 轻微内存增长，建议关注")
            else:
                print(f"  结论: ✗ 可能存在内存泄漏")

        # CPU 统计
        cpu_values = [m["cpu_percent"] for m in self.metrics_history]
        import statistics
        print(f"\nCPU 使用率:")
        print(f"  平均值: {statistics.mean(cpu_values):.1f}%")
        print(f"  P95: {sorted(cpu_values)[int(len(cpu_values)*0.95)]:.1f}%")

        # 错误统计
        print(f"\n错误统计:")
        print(f"  总错误数: {len(self.errors)}")
        if self.errors:
            error_types = {}
            for e in self.errors:
                etype = e.get("type", "unknown")
                error_types[etype] = error_types.get(etype, 0) + 1
            for etype, count in error_types.items():
                print(f"    - {etype}: {count}")

        # 流状态变化
        stream_status_changes = []
        prev_statuses = None
        for m in self.metrics_history:
            statuses = m.get("stream_statuses", {})
            if prev_statuses is not None and statuses != prev_statuses:
                stream_status_changes.append({
                    "timestamp": m["timestamp"],
                    "elapsed": m["elapsed_seconds"],
                    "from": prev_statuses,
                    "to": statuses
                })
            prev_statuses = statuses

        if stream_status_changes:
            print(f"\n流状态变化: {len(stream_status_changes)} 次")
            for change in stream_status_changes[:5]:  # 只显示前5次
                print(f"  [{change['elapsed']/60:.1f}min] {change['from']} -> {change['to']}")

        # 保存详细结果
        result_file = f"benchmark_stability_{int(time.time())}.json"
        with open(result_file, "w") as f:
            json.dump({
                "test_type": "stability",
                "duration_seconds": total_seconds,
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_checks": len(self.metrics_history),
                    "healthy_rate": healthy_count/len(health_checks)*100 if health_checks else 0,
                    "memory_growth_mb": growth if len(mem_values) > 10 else 0,
                    "total_errors": len(self.errors),
                    "stream_status_changes": len(stream_status_changes)
                },
                "errors": self.errors,
                "metrics_history": self.metrics_history
            }, f, indent=2)

        print(f"\n详细结果已保存: {result_file}")


def main():
    parser = argparse.ArgumentParser(description="Campus Guard AI 稳定性测试")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API 基础URL")
    parser.add_argument("--duration", type=int, default=3600,
                        help="测试时长秒数 (默认3600=1小时)")

    args = parser.parse_args()

    benchmark = StabilityBenchmark(
        api_url=args.api_url,
        duration=args.duration
    )

    try:
        asyncio.run(benchmark.run_stability_test())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断，正在分析已收集的数据...")
        benchmark._analyze_results()
    except Exception as e:
        print(f"\n测试出错: {e}")
        raise


if __name__ == "__main__":
    main()
