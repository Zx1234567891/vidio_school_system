"""
ONNX 模型导出工具

支持：
- YOLO 检测模型导出
- YOLO-Pose 姿态模型导出
- 时序行为识别模型导出
"""

import os
from typing import Optional, Tuple
import numpy as np

from ai_runtime.config import settings


class ONNXExporter:
    """ONNX 模型导出器"""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or f"{settings.MODEL_PATH}/onnx"
        os.makedirs(self.output_dir, exist_ok=True)

    def export_yolo_detector(
        self,
        model_name: str = "yolov8n",
        input_shape: Tuple[int, int, int, int] = (1, 3, 640, 640),
        opset_version: int = 11
    ) -> str:
        """
        导出 YOLO 检测模型到 ONNX

        Args:
            model_name: 模型名称
            input_shape: 输入形状 (batch, channels, height, width)
            opset_version: ONNX opset 版本

        Returns:
            导出文件路径
        """
        try:
            from ultralytics import YOLO

            model_path = f"{settings.MODEL_PATH}/{model_name}.pt"
            output_path = f"{self.output_dir}/{model_name}.onnx"

            print(f"[ONNXExporter] Exporting {model_name}...")

            model = YOLO(model_path)
            model.export(
                format="onnx",
                imgsz=input_shape[2:],
                opset=opset_version,
                simplify=True
            )

            # ultralytics 导出到原目录，移动到目标目录
            default_output = model_path.replace(".pt", ".onnx")
            if os.path.exists(default_output):
                os.rename(default_output, output_path)

            print(f"  ✓ Exported to: {output_path}")
            return output_path

        except Exception as e:
            print(f"  ✗ Export failed: {e}")
            raise

    def export_yolo_pose(
        self,
        model_name: str = "yolov8n-pose",
        input_shape: Tuple[int, int, int, int] = (1, 3, 640, 640),
        opset_version: int = 11
    ) -> str:
        """导出 YOLO-Pose 模型到 ONNX"""
        try:
            from ultralytics import YOLO

            model_path = f"{settings.MODEL_PATH}/{model_name}.pt"
            output_path = f"{self.output_dir}/{model_name}.onnx"

            print(f"[ONNXExporter] Exporting {model_name}...")

            model = YOLO(model_path)
            model.export(
                format="onnx",
                imgsz=input_shape[2:],
                opset=opset_version,
                simplify=True
            )

            default_output = model_path.replace(".pt", ".onnx")
            if os.path.exists(default_output):
                os.rename(default_output, output_path)

            print(f"  ✓ Exported to: {output_path}")
            return output_path

        except Exception as e:
            print(f"  ✗ Export failed: {e}")
            raise

    def export_behavior_model(
        self,
        model_path: str,
        input_shape: Tuple[int, ...] = (1, 32, 34),  # (batch, window, features)
        output_path: Optional[str] = None
    ) -> str:
        """
        导出时序行为识别模型到 ONNX

        Args:
            model_path: PyTorch 模型路径
            input_shape: 输入形状
            output_path: 输出路径

        Returns:
            导出文件路径
        """
        try:
            import torch
            import torch.onnx

            output_path = output_path or f"{self.output_dir}/behavior_model.onnx"

            print(f"[ONNXExporter] Exporting behavior model...")

            # 加载 PyTorch 模型
            model = torch.load(model_path, map_location="cpu")
            model.eval()

            # 创建 dummy input
            dummy_input = torch.randn(*input_shape)

            # 导出
            torch.onnx.export(
                model,
                dummy_input,
                output_path,
                export_params=True,
                opset_version=11,
                do_constant_folding=True,
                input_names=["input"],
                output_names=["output"],
                dynamic_axes={
                    "input": {0: "batch_size"},
                    "output": {0: "batch_size"}
                }
            )

            print(f"  ✓ Exported to: {output_path}")
            return output_path

        except Exception as e:
            print(f"  ✗ Export failed: {e}")
            raise

    def verify_onnx_model(self, onnx_path: str) -> bool:
        """验证 ONNX 模型"""
        try:
            import onnx
            import onnxruntime as ort

            # 检查模型
            onnx_model = onnx.load(onnx_path)
            onnx.checker.check_model(onnx_model)

            # 测试推理
            session = ort.InferenceSession(onnx_path)
            input_name = session.get_inputs()[0].name
            input_shape = session.get_inputs()[0].shape

            # 创建测试输入
            test_input = np.random.randn(*[s if s is not None else 1 for s in input_shape]).astype(np.float32)

            # 运行推理
            outputs = session.run(None, {input_name: test_input})

            print(f"[ONNXExporter] Verification passed: {onnx_path}")
            print(f"  Input shape: {input_shape}")
            print(f"  Output shapes: {[o.shape for o in outputs]}")

            return True

        except Exception as e:
            print(f"[ONNXExporter] Verification failed: {e}")
            return False

    def list_exported_models(self) -> list:
        """列出已导出的模型"""
        models = []
        for f in os.listdir(self.output_dir):
            if f.endswith(".onnx"):
                models.append(os.path.join(self.output_dir, f))
        return models


def export_all_models():
    """导出所有模型"""
    exporter = ONNXExporter()

    print("=" * 50)
    print("ONNX Model Export")
    print("=" * 50)

    # 导出 YOLO 检测模型
    try:
        exporter.export_yolo_detector("yolov8n")
    except Exception as e:
        print(f"YOLO detector export skipped: {e}")

    # 导出 YOLO-Pose 模型
    try:
        exporter.export_yolo_pose("yolov8n-pose")
    except Exception as e:
        print(f"YOLO pose export skipped: {e}")

    print("=" * 50)
    print("Export complete!")
    print(f"Models saved to: {exporter.output_dir}")


if __name__ == "__main__":
    export_all_models()
