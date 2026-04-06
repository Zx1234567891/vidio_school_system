#pragma once

#include "stream_core/types.hpp"
#include "stream_core/metrics_collector.hpp"
#include "stream_core/bounded_queue.hpp"
#include "stream_core/ring_buffer.hpp"
#include "stream_core/ffmpeg_decoder.hpp"
#include "stream_core/reconnect_controller.hpp"
#include "stream_core/clip_exporter.hpp"
#include <memory>
#include <atomic>
#include <thread>
#include <functional>

namespace campus_guard {

/**
 * 流会话
 *
 * 管理单路视频流的生命周期，包含：
 * - FFmpeg 解码
 * - 有界队列（背压）
 * - 环形缓冲区（切片导出）
 * - 重连控制
 * - 指标收集
 */
class StreamSession {
public:
    // 帧输出回调
    using FrameOutputCallback = std::function<void(const std::string& stream_id, std::unique_ptr<DecodedFrame>)>;
    // 状态变更回调
    using StatusChangeCallback = std::function<void(const std::string& stream_id, StreamStatus new_status, StreamStatus old_status)>;
    // 错误回调
    using ErrorCallback = std::function<void(const std::string& stream_id, const std::string& error)>;

    explicit StreamSession(const StreamConfig& config);
    ~StreamSession();

    // 禁止拷贝
    StreamSession(const StreamSession&) = delete;
    StreamSession& operator=(const StreamSession&) = delete;

    // 生命周期管理
    bool start();
    void stop();
    void restart();

    // 状态查询
    StreamStatus get_status() const { return status_.load(); }
    StreamMetrics get_metrics() const;
    const std::string& get_id() const { return config_.id; }

    // 配置更新
    void update_config(const StreamConfig& config);

    // 回调设置
    void set_frame_output_callback(FrameOutputCallback callback) { frame_output_callback_ = callback; }
    void set_status_change_callback(StatusChangeCallback callback) { status_change_callback_ = callback; }
    void set_error_callback(ErrorCallback callback) { error_callback_ = callback; }

    // 导出切片
    std::string export_clip(const std::string& event_id, uint32_t seconds_before, uint32_t seconds_after);

    // 获取队列深度
    size_t get_queue_depth() const { return frame_queue_ ? frame_queue_->size() : 0; }

private:
    void set_status(StreamStatus new_status);
    void run();
    void ingest_loop();           // 采集线程
    void process_loop();          // 处理线程
    void handle_frame(std::unique_ptr<DecodedFrame> frame);
    void handle_decode_error(const std::string& error);
    void attempt_reconnect();

    StreamConfig config_;
    std::atomic<StreamStatus> status_{StreamStatus::INIT};
    MetricsCollector metrics_;

    // 核心组件
    std::unique_ptr<FFmpegDecoder> decoder_;
    std::unique_ptr<BoundedQueue<DecodedFrame>> frame_queue_;
    std::unique_ptr<RingBuffer<DecodedFrame>> ring_buffer_;
    std::unique_ptr<ReconnectController> reconnect_controller_;
    std::unique_ptr<ClipExporter> clip_exporter_;

    // 回调
    FrameOutputCallback frame_output_callback_;
    StatusChangeCallback status_change_callback_;
    ErrorCallback error_callback_;

    // 线程控制
    std::atomic<bool> running_{false};
    std::atomic<bool> should_stop_{false};
    std::thread ingest_thread_;
    std::thread process_thread_;

    // 统计
    std::atomic<uint64_t> total_frames_decoded_{0};
    std::atomic<uint64_t> total_bytes_received_{0};
    std::chrono::steady_clock::time_point start_time_;
};

} // namespace campus_guard
