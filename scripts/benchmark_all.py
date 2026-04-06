#!/usr/bin/env python3
"""
Campus Guard AI - 综合压测脚本
一键运行所有性能测试
"""

import subprocess
import sys
import argparse
from pathlib import Path


BENCHMARK_SCRIPTS = {
    "single": {
        "script": "benchmark_single.py",
        "description": "单路延迟测试",
        "default_args": ["--duration", "60"]
    },
    "multi": {
        "script": "benchmark_multi.py",
        "description": "多路并发测试",
        "default_args": ["--streams", "20", "--duration", "300"]
    },
    "stability": {
        "script": "benchmark_stability.py",
        "description": "稳定性测试",
        "default_args": ["--duration", "3600"]
    },
    "clip": {
        "script": "benchmark_clip_export.py",
        "description": "切片导出测试",
        "default_args": ["--count", "10"]
    },
    "websocket": {
        "script": "benchmark_websocket.py",
        "description": "WebSocket 延迟测试",
        "default_args": ["--count", "50"]
    }
}


def run_benchmark(name: str, api_url: str, extra_args: list = None):
    """运行单个测试"""
    config = BENCHMARK_SCRIPTS.get(name)
    if not config:
        print(f"未知测试: {name}")
        return False

    script_path = Path(__file__).parent / config["script"]
    if not script_path.exists():
        print(f"脚本不存在: {script_path}")
        return False

    print(f"\n{'='*60}")
    print(f"运行: {config['description']}")
    print(f"{'='*60}")

    cmd = [sys.executable, str(script_path), "--api-url", api_url]
    cmd.extend(config["default_args"])
    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print(f"\n{name} 测试被中断")
        return False
    except Exception as e:
        print(f"运行出错: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Campus Guard AI 综合压测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行所有测试
  python benchmark_all.py

  # 只运行单路和多路测试
  python benchmark_all.py --tests single multi

  # 快速测试模式（缩短时长）
  python benchmark_all.py --quick

  # 指定 API 地址
  python benchmark_all.py --api-url http://192.168.1.100:8000
        """
    )
    parser.add_argument("--api-url", default="http://localhost:8000", help="API 基础URL")
    parser.add_argument("--tests", nargs="+", choices=list(BENCHMARK_SCRIPTS.keys()),
                        help="指定要运行的测试")
    parser.add_argument("--quick", action="store_true", help="快速模式（缩短测试时长）")
    parser.add_argument("--list", action="store_true", help="列出可用测试")

    args = parser.parse_args()

    if args.list:
        print("可用测试:")
        for name, config in BENCHMARK_SCRIPTS.items():
            print(f"  {name:12} - {config['description']}")
        return

    # 确定要运行的测试
    tests_to_run = args.tests or list(BENCHMARK_SCRIPTS.keys())

    # 快速模式覆盖默认参数
    extra_args = []
    if args.quick:
        print("快速模式: 缩短测试时长")
        # 通过环境变量或修改默认参数来实现
        # 这里简化处理，实际使用时可以调整

    print(f"\n{'='*60}")
    print(f"Campus Guard AI - 综合压测")
    print(f"{'='*60}")
    print(f"API地址: {args.api_url}")
    print(f"测试项: {', '.join(tests_to_run)}")
    print(f"{'='*60}")

    results = {}
    for test_name in tests_to_run:
        success = run_benchmark(test_name, args.api_url, extra_args)
        results[test_name] = success

    # 汇总结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")

    for name, success in results.items():
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {name:12} {status}")

    passed = sum(1 for s in results.values() if s)
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")


if __name__ == "__main__":
    main()
