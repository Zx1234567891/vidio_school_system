"""
视频行为检测测试总结与优化建议

当前状态 (2024-04-05):
===================

1. 吸烟视频 (吸烟.mp4):
   ✅ 成功检测到 smoking (602次, 平均置信度0.919)
   ⚠️ 同时检测到 loitering (需要优化区分)

2. 低头看手机视频 (低头看手机.mp4):
   ✅ 成功检测到 phone_use
   ❌ 大量误报: vandalism, camera_blocking, bullying, falling, fighting, fence_climbing, smoking

3. 其他视频:
   待测试

问题分析:
=========

1. 误报原因:
   - 检测器阈值过于宽松
   - 不同行为的特征有重叠（如吸烟和手机使用都涉及手腕靠近脸部）
   - 需要更多特定于行为的区分特征

2. 小目标检测问题:
   - 吸烟视频中的人物较小，需要降低检测置信度阈值
   - 已修改 config.py: DETECTOR_CONFIDENCE = 0.3

优化建议:
=========

1. 立即可做的优化:
   - 提高各个检测器的 min_frames 要求
   - 提高 velocity_threshold 减少误报
   - 添加更多排除条件（如吸烟时头部不能太低）

2. 长期优化方案:
   - 使用专门的行为识别模型（如 SlowFast, I3D）替代规则引擎
   - 训练自定义模型针对校园场景
   - 添加时序一致性检查（如一个行为应该持续一段时间）

关键文件修改:
=============

1. services/ai-runtime/src/ai_runtime/config.py
   - DETECTOR_CONFIDENCE: 0.5 -> 0.3 (检测小目标)

2. services/ai-runtime/src/ai_runtime/behavior/behavior_recognizer.py
   - 修复了语法错误
   - 优化了吸烟检测器参数
   - 添加了更多特征提取

测试命令:
=========

cd services/ai-runtime
python video_test.py

或测试单个视频:
python -c "
import sys; sys.path.insert(0, 'src')
# 测试代码见 video_test.py
"

下一步工作:
===========

1. 针对每个视频类型调整检测器阈值
2. 添加行为优先级机制（如检测到 phone_use 时不应该同时检测到 smoking）
3. 实现行为切换逻辑（一个人不能同时做两件互斥的事情）
4. 添加更多视频样本进行交叉验证
"""
