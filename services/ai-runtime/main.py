"""
Campus Guard AI Runtime

AI 推理运行时服务 - P2 实现
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uvicorn
import numpy as np

from ai_runtime.config import settings
from ai_runtime.pipeline import create_pipeline, AIPipeline
from ai_runtime.models import (
    BehaviorEvent, PipelineResult, EventType,
    Severity, RuleType
)
from ai_runtime.rules.rule_engine import RuleConfig

app = FastAPI(
    title="Campus Guard AI Runtime",
    description="AI 推理运行时服务 - 检测/跟踪/行为识别/规则融合",
    version="0.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 Pipeline
pipeline: Optional[AIPipeline] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: bool
    timestamp: str


class InferenceRequest(BaseModel):
    frame_id: str
    stream_id: str
    timestamp: float
    # 图像数据（base64 编码或 URL）
    image_data: Optional[str] = None
    # 或提供图像尺寸用于测试
    width: int = 640
    height: int = 480


class InferenceResponse(BaseModel):
    frame_id: str
    stream_id: str
    detections_count: int
    tracks_count: int
    events: List[BehaviorEvent]
    processing_time_ms: float


class RuleConfigRequest(BaseModel):
    rule_id: str
    rule_name: str
    rule_type: str
    enabled: bool = True
    polygon: Optional[List[tuple]] = None
    line: Optional[List[tuple]] = None
    threshold: float = 10.0
    severity: str = "medium"
    stream_id: Optional[str] = None


@app.on_event("startup")
async def startup():
    """启动时初始化 Pipeline"""
    global pipeline

    print("=" * 50)
    print("Campus Guard AI Runtime Starting...")
    print("=" * 50)

    # 使用 Mock 模式启动（无需真实模型）
    pipeline = create_pipeline(use_real_models=False, device=settings.INFERENCE_DEVICE)

    print("=" * 50)
    print("AI Runtime Ready!")
    print("=" * 50)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version="0.2.0",
        models_loaded=pipeline is not None and pipeline.is_ready(),
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/inference", response_model=InferenceResponse)
async def inference(request: InferenceRequest):
    """单帧推理"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    import time
    start = time.time()

    try:
        # 创建模拟图像（实际应解码 image_data）
        image = np.random.randint(0, 255, (request.height, request.width, 3), dtype=np.uint8)

        # 执行推理
        result = pipeline.process_frame(
            image=image,
            stream_id=request.stream_id,
            frame_id=request.frame_id
        )

        processing_time = (time.time() - start) * 1000

        return InferenceResponse(
            frame_id=request.frame_id,
            stream_id=request.stream_id,
            detections_count=len(result.frame_result.detections),
            tracks_count=len(result.tracks),
            events=result.events,
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rules")
async def add_rule(request: RuleConfigRequest):
    """添加规则"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    config = RuleConfig(
        rule_id=request.rule_id,
        rule_name=request.rule_name,
        rule_type=RuleType(request.rule_type),
        enabled=request.enabled,
        polygon=request.polygon,
        line=request.line,
        threshold=request.threshold,
        severity=Severity(request.severity),
        stream_id=request.stream_id
    )

    pipeline.add_rule(config)

    return {"message": "Rule added", "rule_id": request.rule_id}


@app.get("/models")
async def list_models():
    """列出可用模型"""
    return {
        "detector": {
            "name": "YOLOv8",
            "version": "8.0.0",
            "status": "ready" if pipeline and pipeline.detector.is_ready() else "not_loaded",
            "classes": ["person", "phone", "smoke", "fire", "bag", "camera"]
        },
        "tracker": {
            "name": "ByteTrack",
            "version": "1.0.0",
            "status": "ready"
        },
        "pose": {
            "name": "YOLO-Pose",
            "version": "8.0.0",
            "status": "ready" if pipeline and pipeline.pose_estimator.is_ready() else "not_loaded"
        },
        "behavior": {
            "name": "Temporal Behavior Recognizer",
            "version": "1.0.0",
            "status": "ready",
            "window_sizes": [16, 32, 64]
        }
    }


@app.post("/models/{model_name}/export")
async def export_model(model_name: str, background_tasks: BackgroundTasks):
    """导出模型到 ONNX"""
    from ai_runtime.models.onnx_exporter import ONNXExporter

    exporter = ONNXExporter()

    try:
        if model_name == "yolo":
            path = exporter.export_yolo_detector()
        elif model_name == "pose":
            path = exporter.export_yolo_pose()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")

        return {"message": "Model exported", "path": path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/active")
async def get_active_events():
    """获取当前活跃事件"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    # 强制完成待处理事件
    events = pipeline.flush_events()

    return {
        "count": len(events),
        "events": events
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
