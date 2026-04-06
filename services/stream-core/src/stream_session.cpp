#include "stream_core/stream_session.hpp"
#include "stream_core/types.hpp"

#include <iostream>
#include <chrono>

namespace campus_guard {

StreamSession::StreamSession(const StreamConfig& config)
    : config_(config) {
    // 初始化重连控制器配置
    ReconnectController::Config reconnect_config;
    reconnect_config.max_attempts = config.max_reconnect_attempts;
    reconnect_config.initial_interval_ms = config.reconnect_interval_ms;
    reconnect_config.max_interval_ms = 30000;
    reconnect_config.backoff_multiplier = 2.0;
    reconnect_controller_ = std::make_unique<ReconnectController>(reconnect_config);

    // 初始化导出器配置
    ClipExporter::Config exporter_config;
    exporter_config.output_dir = "./clips";
    exporter_config.filename_prefix = "clip";
    exporter_config.duration_seconds = 10;
    exporter_config.fps = static_cast<uint32_t>(config.target_fps);
    exporter_config.quality = 23;
    clip_exporter_ = std::make_unique<ClipExporter>(exporter_config);

    // 初始化队列和缓冲区
    frame_queue_ = std::make_unique<BoundedQueue<DecodedFrame>>(config.max_queue_size);
    ring_buffer_ = std::make_unique<RingBuffer<DecodedFrame>>(config.target_fps * config.ring_buffer_seconds);

    // 初始化导出器
    clip_exporter_->initialize();

    std::cout << "[StreamSession] Created: " << config_.id
              << " (queue_size=" << config.max_queue_size
              << ", ring_buffer=" << config.target_fps * config.ring_buffer_seconds << " frames)"
              << std::endl;
}

StreamSession::~StreamSession() {
    stop();
}

bool StreamSession::start() {
    if (running_.exchange(true)) {
        return false;  // 已经在运行
    }

    should_stop_ = false;
    reconnect_controller_->reset();
    start_time_ = std::chrono::steady_clock::now();

    // 创建解码器
    decoder_ = std::make_unique<FFmpegDecoder>();

    // 设置解码器回调
    decoder_->set_frame_callback([this](std::unique_ptr<DecodedFrame> frame) {
        handle_frame(std::move(frame));
    });

    decoder_->set_error_callback([this](const std::string& error) {
        handle_decode_error(error);
    });

    // 打开输入源
    set_status(StreamStatus::CONNECTING);

    if (!decoder_->open(config_.url, config_.input_type)) {
        std::cerr << "[StreamSession] Failed to open: " << config_.url << std::endl;
        set_status(StreamStatus::ERROR);
        running_ = false;
        return false;
    }

    // 启动线程
    ingest_thread_ = std::thread(&StreamSession::ingest_loop, this);
    process_thread_ = std::thread(&StreamSession::process_loop, this);

    set_status(StreamStatus::RUNNING);

    std::cout << "[StreamSession] Started: " << config_.id << std::endl;
    return true;
}

void StreamSession::stop() {
    if (!running_.exchange(false)) {
        return;
    }

    should_stop_ = true;

    // 停止解码器
    if (decoder_) {
        decoder_->stop_decode_loop();
    }

    // 关闭队列
    if (frame_queue_) {
        frame_queue_->shutdown();
    }

    // 等待线程结束
    if (ingest_thread_.joinable()) {
        ingest_thread_.join();
    }
    if (process_thread_.joinable()) {
        process_thread_.join();
    }

    // 关闭解码器
    if (decoder_) {
        decoder_->close();
        decoder_.reset();
    }

    set_status(StreamStatus::STOPPED);

    std::cout << "[StreamSession] Stopped: " << config_.id << std::endl;
}

void StreamSession::restart() {
    std::cout << "[StreamSession] Restarting: " << config_.id << std::endl;
    stop();
    metrics_.reset();
    total_frames_decoded_ = 0;
    reconnect_controller_->reset();
    start();
}

void StreamSession::update_config(const StreamConfig& config) {
    config_ = config;
}

StreamMetrics StreamSession::get_metrics() const {
    auto metrics = metrics_.get_metrics();

    // 添加扩展指标
    metrics.total_frames_decoded = total_frames_decoded_.load();
    metrics.total_bytes_received = total_bytes_received_.load();

    // 计算运行时间
    auto now = std::chrono::steady_clock::now();
    auto uptime = std::chrono::duration_cast<std::chrono::seconds>(now - start_time_);
    metrics.uptime = uptime;

    // 计算码率（简化计算）
    if (uptime.count() > 0) {
        metrics.bitrate_kbps = (metrics.total_bytes_received * 8.0 / 1000.0) / uptime.count();
    }

    // 队列深度
    metrics.queue_depth = get_queue_depth();

    return metrics;
}

void StreamSession::set_status(StreamStatus new_status) {
    StreamStatus old_status = status_.exchange(new_status);
    if (old_status != new_status && status_change_callback_) {
        status_change_callback_(config_.id, new_status, old_status);
    }
}

void StreamSession::ingest_loop() {
    // 启动解码循环
    decoder_->start_decode_loop();

    // 等待停止信号
    while (!should_stop_) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        // 更新指标
        metrics_.update_fps(decoder_->get_fps());
    }

    decoder_->stop_decode_loop();
}

void StreamSession::process_loop() {
    while (!should_stop_) {
        auto frame_opt = frame_queue_->pop_for(std::chrono::milliseconds(100));

        if (!frame_opt.has_value()) {
            continue;
        }

        auto& frame = frame_opt.value();

        auto start = std::chrono::steady_clock::now();

        // 存入环形缓冲区
        ring_buffer_->push(std::move(frame));

        // 更新处理延迟
        auto end = std::chrono::steady_clock::now();
        auto latency = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count() / 1000.0;
        metrics_.update_decode_latency(latency);

        ++total_frames_decoded_;
    }
}

void StreamSession::handle_frame(std::unique_ptr<DecodedFrame> frame) {
    if (!frame || !frame->frame) {
        return;
    }

    // 统计接收字节数
    total_bytes_received_ += frame->frame->size();

    // 尝试推入队列（背压策略）
    bool pushed = frame_queue_->try_push(std::move(*frame));

    if (!pushed) {
        // 队列满，增加丢帧计数
        metrics_.increment_dropped_frames();
    } else {
        // 通知外部
        if (frame_output_callback_) {
            // 注意：这里简化处理，实际应该传递拷贝或共享指针
            // frame_output_callback_(config_.id, std::move(frame));
        }
    }
}

void StreamSession::handle_decode_error(const std::string& error) {
    std::cerr << "[StreamSession] Decode error: " << error << std::endl;

    if (error_callback_) {
        error_callback_(config_.id, error);
    }

    // 尝试重连
    if (!should_stop_) {
        attempt_reconnect();
    }
}

void StreamSession::attempt_reconnect() {
    if (!reconnect_controller_->should_reconnect()) {
        std::cerr << "[StreamSession] Reconnect exhausted for: " << config_.id << std::endl;
        set_status(StreamStatus::ERROR);
        return;
    }

    set_status(StreamStatus::RECONNECTING);

    uint32_t wait_ms = reconnect_controller_->get_next_wait_time();
    std::cout << "[StreamSession] Reconnecting in " << wait_ms << "ms..." << std::endl;

    std::this_thread::sleep_for(std::chrono::milliseconds(wait_ms));

    // 关闭当前连接
    if (decoder_) {
        decoder_->close();
    }

    // 重新打开
    if (decoder_->open(config_.url, config_.input_type)) {
        reconnect_controller_->record_attempt();
        metrics_.increment_reconnect_count();
        set_status(StreamStatus::RUNNING);
        std::cout << "[StreamSession] Reconnected: " << config_.id << std::endl;
    } else {
        // 重连失败，继续尝试
        attempt_reconnect();
    }
}

std::string StreamSession::export_clip(const std::string& event_id, uint32_t seconds_before, uint32_t seconds_after) {
    // 从环形缓冲区获取帧
    size_t frame_count = config_.target_fps * (seconds_before + seconds_after);
    auto frames = ring_buffer_->get_recent(frame_count);

    // 导出切片
    return clip_exporter_->export_clip(frames, event_id);
}

} // namespace campus_guard
