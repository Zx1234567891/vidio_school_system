"""
Campus Guard AI Runtime

AI 推理运行时服务 - P2 实现
"""

import base64
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_runtime.config import settings
from ai_runtime.pipeline import create_pipeline, AIPipeline
from ai_runtime.models import (
    BehaviorEvent, PipelineResult, EventType,
    Severity, RuleType, Detection
)
from ai_runtime.rules.rule_engine import RuleConfig
from ai_runtime.detector.annotate import draw_detections
from ai_runtime.detector.detector import YOLODetector

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
    # 图像数据：base64 编码的 JPEG / PNG 字节
    image_data: Optional[str] = None
    # 无 image_data 时用以下尺寸生成随机图（仅调试）
    width: int = 640
    height: int = 480
    # 是否返回叠加后的 JPEG（base64）
    return_annotated: bool = True
    # 叠加 JPEG 的质量 1-100
    jpeg_quality: int = 75


class DetectionOut(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    severity: str
    # 像素坐标（左上 + 右下）
    bbox: List[int]


class InferenceResponse(BaseModel):
    frame_id: str
    stream_id: str
    detections_count: int
    tracks_count: int
    detections: List[DetectionOut]
    events: List[BehaviorEvent]
    processing_time_ms: float
    device: str
    # 叠加后的 JPEG（base64），return_annotated=False 时为空
    annotated_jpeg_b64: Optional[str] = None


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
    """启动时初始化 Pipeline（优先真实 YOLO26 + CUDA，加载失败自动降级）"""
    global pipeline

    print("=" * 50)
    print("Campus Guard AI Runtime Starting...")
    print(f"  device         : {settings.INFERENCE_DEVICE}")
    print(f"  detector_model : {settings.DETECTOR_MODEL}")
    print(f"  use_real_models: {settings.USE_REAL_MODELS}")
    print("=" * 50)

    pipeline = create_pipeline(
        use_real_models=settings.USE_REAL_MODELS,
        device=settings.INFERENCE_DEVICE,
    )

    # 若配置了真实模型但检测器加载失败，回退到 mock，保证服务可启动
    if settings.USE_REAL_MODELS and not pipeline.detector.is_ready():
        print("[warn] 真实检测器加载失败，回退到 mock 检测器")
        pipeline = create_pipeline(use_real_models=False, device="cpu")

    print("=" * 50)
    print(f"AI Runtime Ready! (detector_ready={pipeline.detector.is_ready()})")
    print("=" * 50)


def _decode_image(b64: str) -> np.ndarray:
    """把 base64 JPEG/PNG 字节解成 BGR ndarray。"""
    raw = base64.b64decode(b64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("image_data 无法解码，需为 JPEG/PNG 的 base64")
    return img


def _encode_jpeg_b64(img: np.ndarray, quality: int) -> str:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise RuntimeError("JPEG 编码失败")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _det_to_out(det: Detection, w: int, h: int) -> DetectionOut:
    x1 = int(det.bbox.x * w)
    y1 = int(det.bbox.y * h)
    x2 = int((det.bbox.x + det.bbox.width) * w)
    y2 = int((det.bbox.y + det.bbox.height) * h)
    return DetectionOut(
        class_id=det.class_id,
        class_name=det.class_name,
        confidence=round(float(det.confidence), 4),
        severity=YOLODetector.BEHAVIOR_SEVERITY.get(det.class_name, "info"),
        bbox=[x1, y1, x2, y2],
    )


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
    """单帧推理：接收 base64 JPEG/PNG，返回检测列表与叠加后的 JPEG。"""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    start = time.time()

    try:
        if request.image_data:
            image = _decode_image(request.image_data)
        else:
            # 调试用：生成随机图
            image = np.random.randint(0, 255, (request.height, request.width, 3), dtype=np.uint8)

        h, w = image.shape[:2]

        result = pipeline.process_frame(
            image=image,
            stream_id=request.stream_id,
            frame_id=request.frame_id,
        )

        dets_out = [_det_to_out(d, w, h) for d in result.frame_result.detections]

        annotated_b64: Optional[str] = None
        if request.return_annotated:
            annotated = image.copy()
            draw_detections(annotated, result.frame_result.detections)
            annotated_b64 = _encode_jpeg_b64(annotated, request.jpeg_quality)

        processing_time = (time.time() - start) * 1000

        return InferenceResponse(
            frame_id=request.frame_id,
            stream_id=request.stream_id,
            detections_count=len(result.frame_result.detections),
            tracks_count=len(result.tracks),
            detections=dets_out,
            events=result.events,
            processing_time_ms=processing_time,
            device=getattr(pipeline.detector, "device", "cpu"),
            annotated_jpeg_b64=annotated_b64,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    detector_ready = bool(pipeline and pipeline.detector.is_ready())
    return {
        "detector": {
            "name": "YOLO26 (自训练 · 校园行为)",
            "weights": f"{settings.DETECTOR_MODEL}.pt",
            "device": getattr(pipeline.detector, "device", "cpu") if pipeline else "unknown",
            "status": "ready" if detector_ready else "not_loaded",
            "classes": list(YOLODetector.CLASS_NAMES.values()),
            "severity": YOLODetector.BEHAVIOR_SEVERITY,
        },
        "tracker": {
            "name": "ByteTrack",
            "version": "1.0.0",
            "status": "ready",
        },
        "pose": {
            "name": "YOLO-Pose",
            "version": "8.0.0",
            "status": "ready" if pipeline and pipeline.pose_estimator.is_ready() else "not_loaded",
        },
        "behavior": {
            "name": "Temporal Behavior Recognizer",
            "version": "1.0.0",
            "status": "ready",
            "window_sizes": [16, 32, 64],
        },
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
