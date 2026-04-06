#include "stream_core/stream_manager.hpp"
#include "stream_core/types.hpp"

#include <iostream>
#include <sstream>
#include <iomanip>

namespace campus_guard {

StreamManager::StreamManager(size_t thread_pool_size)
    : thread_pool_(std::make_unique<ThreadPool>(thread_pool_size)) {
    std::cout << "[StreamManager] Created with thread pool size: " << thread_pool_size << std::endl;
}

StreamManager::~StreamManager() {
    // 停止所有流
    std::unique_lock<std::mutex> lock(streams_mutex_);
    for (auto& [id, session] : streams_) {
        if (session) {
            session->stop();
        }
    }
    streams_.clear();

    std::cout << "[StreamManager] Destroyed" << std::endl;
}

std::string StreamManager::create_stream(const StreamConfig& config) {
    std::unique_lock<std::mutex> lock(streams_mutex_);

    if (streams_.size() >= MAX_STREAMS) {
        throw std::runtime_error("Maximum number of streams (" + std::to_string(MAX_STREAMS) + ") reached");
    }

    // 生成唯一 ID
    uint32_t id = ++stream_counter_;
    std::stringstream ss;
    ss << "stream_" << std::setw(4) << std::setfill('0') << id;
    std::string stream_id = ss.str();

    // 创建会话
    StreamConfig stream_config = config;
    stream_config.id = stream_id;

    auto session = std::make_shared<StreamSession>(stream_config);
    apply_callbacks(session);

    streams_[stream_id] = session;

    std::cout << "[StreamManager] Created stream: " << stream_id << std::endl;
    return stream_id;
}

bool StreamManager::remove_stream(const std::string& stream_id) {
    std::unique_lock<std::mutex> lock(streams_mutex_);

    auto it = streams_.find(stream_id);
    if (it == streams_.end()) {
        return false;
    }

    if (it->second) {
        it->second->stop();
    }

    streams_.erase(it);
    std::cout << "[StreamManager] Removed stream: " << stream_id << std::endl;
    return true;
}

std::shared_ptr<StreamSession> StreamManager::get_stream(const std::string& stream_id) {
    std::unique_lock<std::mutex> lock(streams_mutex_);

    auto it = streams_.find(stream_id);
    if (it != streams_.end()) {
        return it->second;
    }
    return nullptr;
}

bool StreamManager::start_stream(const std::string& stream_id) {
    auto session = get_stream(stream_id);
    if (!session) {
        return false;
    }
    return session->start();
}

bool StreamManager::stop_stream(const std::string& stream_id) {
    auto session = get_stream(stream_id);
    if (!session) {
        return false;
    }
    session->stop();
    return true;
}

bool StreamManager::restart_stream(const std::string& stream_id) {
    auto session = get_stream(stream_id);
    if (!session) {
        return false;
    }
    session->restart();
    return true;
}

std::vector<std::string> StreamManager::list_stream_ids() const {
    std::unique_lock<std::mutex> lock(streams_mutex_);

    std::vector<std::string> ids;
    ids.reserve(streams_.size());

    for (const auto& [id, _] : streams_) {
        ids.push_back(id);
    }

    return ids;
}

size_t StreamManager::get_stream_count() const {
    std::unique_lock<std::mutex> lock(streams_mutex_);
    return streams_.size();
}

size_t StreamManager::get_active_stream_count() const {
    std::unique_lock<std::mutex> lock(streams_mutex_);

    size_t active = 0;
    for (const auto& [_, session] : streams_) {
        if (session && session->get_status() == StreamStatus::RUNNING) {
            ++active;
        }
    }

    return active;
}

void StreamManager::set_frame_output_callback(FrameOutputCallback callback) {
    frame_output_callback_ = callback;

    // 应用到现有流
    std::unique_lock<std::mutex> lock(streams_mutex_);
    for (auto& [_, session] : streams_) {
        if (session) {
            session->set_frame_output_callback(callback);
        }
    }
}

void StreamManager::set_status_change_callback(StatusChangeCallback callback) {
    status_change_callback_ = callback;

    std::unique_lock<std::mutex> lock(streams_mutex_);
    for (auto& [_, session] : streams_) {
        if (session) {
            session->set_status_change_callback(callback);
        }
    }
}

void StreamManager::set_error_callback(ErrorCallback callback) {
    error_callback_ = callback;

    std::unique_lock<std::mutex> lock(streams_mutex_);
    for (auto& [_, session] : streams_) {
        if (session) {
            session->set_error_callback(callback);
        }
    }
}

void StreamManager::apply_callbacks(const std::shared_ptr<StreamSession>& session) {
    if (!session) return;

    if (frame_output_callback_) {
        session->set_frame_output_callback(frame_output_callback_);
    }
    if (status_change_callback_) {
        session->set_status_change_callback(status_change_callback_);
    }
    if (error_callback_) {
        session->set_error_callback(error_callback_);
    }
}

std::string StreamManager::export_clip(
    const std::string& stream_id,
    const std::string& event_id,
    uint32_t seconds_before,
    uint32_t seconds_after) {

    auto session = get_stream(stream_id);
    if (!session) {
        return "";
    }

    return session->export_clip(event_id, seconds_before, seconds_after);
}

StreamManager::GlobalMetrics StreamManager::get_global_metrics() const {
    GlobalMetrics metrics{};
    metrics.total_streams = get_stream_count();
    metrics.active_streams = get_active_stream_count();
    metrics.thread_pool_size = thread_pool_->get_thread_count();
    metrics.pending_tasks = thread_pool_->get_pending_count();

    // 汇总所有流的指标
    std::unique_lock<std::mutex> lock(streams_mutex_);
    for (const auto& [_, session] : streams_) {
        if (session) {
            auto stream_metrics = session->get_metrics();
            metrics.total_frames_decoded += stream_metrics.total_frames_decoded;
            metrics.total_dropped_frames += stream_metrics.dropped_frames;
        }
    }

    return metrics;
}

} // namespace campus_guard
