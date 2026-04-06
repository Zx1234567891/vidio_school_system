#pragma once

#include "stream_core/types.hpp"
#include <atomic>
#include <chrono>

namespace campus_guard {

/**
 * 指标收集器
 *
 * 收集每路流的性能指标
 */
class MetricsCollector {
public:
    MetricsCollector();

    // 更新指标
    void update_fps(double fps);
    void update_queue_depth(size_t depth);
    void increment_dropped_frames(uint64_t count = 1);
    void update_decode_latency(double latency_ms);
    void increment_reconnect_count();
    void record_frame_received();

    // 获取当前指标
    StreamMetrics get_metrics() const;

    // 重置
    void reset();

private:
    std::atomic<double> fps_{0.0};
    std::atomic<size_t> queue_depth_{0};
    std::atomic<uint64_t> dropped_frames_{0};
    std::atomic<double> decode_latency_ms_{0.0};
    std::atomic<uint32_t> reconnect_count_{0};
    std::chrono::steady_clock::time_point start_time_;
};

} // namespace campus_guard
