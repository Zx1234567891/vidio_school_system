#include "stream_core/metrics_collector.hpp"

namespace campus_guard {

MetricsCollector::MetricsCollector()
    : start_time_(std::chrono::steady_clock::now()) {}

void MetricsCollector::update_fps(double fps) {
    fps_.store(fps, std::memory_order_relaxed);
}

void MetricsCollector::update_queue_depth(size_t depth) {
    queue_depth_.store(depth, std::memory_order_relaxed);
}

void MetricsCollector::increment_dropped_frames(uint64_t count) {
    dropped_frames_.fetch_add(count, std::memory_order_relaxed);
}

void MetricsCollector::update_decode_latency(double latency_ms) {
    decode_latency_ms_.store(latency_ms, std::memory_order_relaxed);
}

void MetricsCollector::increment_reconnect_count() {
    reconnect_count_.fetch_add(1, std::memory_order_relaxed);
}

void MetricsCollector::record_frame_received() {
    // 用于计算 FPS
}

StreamMetrics MetricsCollector::get_metrics() const {
    auto now = std::chrono::steady_clock::now();
    auto uptime = std::chrono::duration_cast<std::chrono::seconds>(now - start_time_);

    return StreamMetrics{
        fps_.load(std::memory_order_relaxed),
        queue_depth_.load(std::memory_order_relaxed),
        dropped_frames_.load(std::memory_order_relaxed),
        decode_latency_ms_.load(std::memory_order_relaxed),
        reconnect_count_.load(std::memory_order_relaxed),
        uptime
    };
}

void MetricsCollector::reset() {
    fps_.store(0.0);
    queue_depth_.store(0);
    dropped_frames_.store(0);
    decode_latency_ms_.store(0.0);
    reconnect_count_.store(0);
    start_time_ = std::chrono::steady_clock::now();
}

} // namespace campus_guard
