---
name: perf-benchmark
description: 为校园安防系统建立真实性能测试与压测脚本，覆盖单路延迟、多路并发、稳定性、丢帧、重连、浏览器端渲染压力
disable-model-invocation: true
---

为当前项目建立 benchmark 与 stress test 体系。

测试目标：
- 单路 1080P 延迟
- 多路并发吞吐
- 长时间稳定性
- reconnect 稳定性
- 前端多宫格渲染压力
- clip export 速度
- WebSocket 实时推送延迟

输出物：
1. benchmark scripts
2. stress test scripts
3. metrics schema
4. benchmark.md
5. 可复现的运行命令

必须统计：
- ingest fps
- decode latency
- inference latency
- end-to-end alert latency
- queue depth
- dropped frames
- reconnect count
- memory
- cpu
- gpu（如果存在）
- browser render fps（如果可测）

规则：
- 禁止伪造数字
- 输出 p50 / p95 / p99
- 标注测试数据来源和硬件环境
