---
paths:
  - "services/ai-runtime/**/*"
---

# AI Runtime 规则

## 目标
建立可插拔的检测、跟踪、行为识别、规则融合与模型训练/导出路径。

## 推荐 pipeline
1. detection
2. tracking
3. temporal feature extraction
4. behavior classifier
5. rule fusion
6. event aggregation
7. review feedback loop

## 核心约束
- 不把多人交互理解简化成单标签分类
- 事件输出必须绑定 track 和 participants
- 支持 ROI / polygon / dwell-time / intrusion 等规则类行为
- 支持 bullying 与 mutual-fight 的差异输出
- 支持 ONNX 导出与 ONNX Runtime 加载路径
- baseline provider 可以先使用 mock 或轻量模型，但接口必须真实可替换

## 输出结构要求
- 支持单人行为与多人交互行为
- 支持角色：
  - aggressor
  - victim
  - bystander
- 事件聚合必须具备时间窗口概念
- 输出必须能驱动历史查询、审核和导出
