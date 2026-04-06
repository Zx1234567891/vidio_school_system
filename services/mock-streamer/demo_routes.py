"""
演示模式API路由 - 提供模拟数据接口
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import os
import sys

# 添加mock-streamer到路径
sys.path.insert(0, os.path.dirname(__file__))

from mock_streamer import get_streamer, init_streamer
from demo_data_generator import DemoDataGenerator

router = APIRouter()

# 演示数据生成器
demo_generator: DemoDataGenerator = None


def init_demo_mode(video_dir: str):
    """初始化演示模式"""
    global demo_generator

    # 初始化推流器
    streamer = init_streamer(video_dir)

    # 生成演示数据
    demo_generator = DemoDataGenerator()
    demo_generator.generate_all_demo_data(streamer.get_all_streams())

    print(f"[*] 演示模式已初始化:")
    print(f"    - 视频流: {len(streamer.streams)}")
    print(f"    - 事件数: {len(demo_generator.events)}")
    print(f"    - 告警数: {len(demo_generator.alerts)}")

    return streamer, demo_generator


@router.get("/demo/streams")
async def get_demo_streams() -> Dict[str, Any]:
    """获取所有演示视频流"""
    streamer = get_streamer()
    if not streamer:
        raise HTTPException(status_code=503, detail="演示模式未初始化")

    return {
        "code": 0,
        "data": {
            "items": streamer.get_all_streams(),
            "total": len(streamer.streams)
        }
    }


@router.post("/demo/streams/{stream_id}/start")
async def start_demo_stream(stream_id: str) -> Dict[str, Any]:
    """启动演示推流"""
    streamer = get_streamer()
    if not streamer:
        raise HTTPException(status_code=503, detail="演示模式未初始化")

    if streamer.start_stream(stream_id):
        return {"code": 0, "message": "推流已启动"}
    raise HTTPException(status_code=404, detail="流不存在")


@router.post("/demo/streams/{stream_id}/stop")
async def stop_demo_stream(stream_id: str) -> Dict[str, Any]:
    """停止演示推流"""
    streamer = get_streamer()
    if not streamer:
        raise HTTPException(status_code=503, detail="演示模式未初始化")

    if streamer.stop_stream(stream_id):
        return {"code": 0, "message": "推流已停止"}
    raise HTTPException(status_code=404, detail="流不存在")


@router.get("/demo/events")
async def get_demo_events(limit: int = 50) -> Dict[str, Any]:
    """获取演示事件"""
    if not demo_generator:
        raise HTTPException(status_code=503, detail="演示模式未初始化")

    return {
        "code": 0,
        "data": {
            "items": demo_generator.get_recent_events(limit),
            "total": len(demo_generator.events)
        }
    }


@router.get("/demo/alerts")
async def get_demo_alerts() -> Dict[str, Any]:
    """获取演示告警"""
    if not demo_generator:
        raise HTTPException(status_code=503, detail="演示模式未初始化")

    return {
        "code": 0,
        "data": {
            "items": demo_generator.get_unacknowledged_alerts(),
            "total": len(demo_generator.alerts)
        }
    }


@router.get("/demo/stats")
async def get_demo_stats() -> Dict[str, Any]:
    """获取演示统计"""
    if not demo_generator:
        raise HTTPException(status_code=503, detail="演示模式未初始化")

    streamer = get_streamer()
    stream_stats = streamer.get_stats() if streamer else {}

    return {
        "code": 0,
        "data": {
            **demo_generator.get_stats(),
            **stream_stats
        }
    }
