#pragma once

#include "stream_core/stream_session.hpp"
#include "stream_core/thread_pool.hpp"
#include <memory>
#include <unordered_map>
#include <mutex>
#include <string>
#include <functional>

namespace campus_guard {

/**
 * 流管理器
 *
 * 管理最多 20 路视频流
 */
class StreamManager {
public:
    static constexpr size_t MAX_STREAMS = 20;
    static constexpr size_t DEFAULT_THREAD_POOL_SIZE = 8;

    // 全局回调类型
    using FrameOutputCallback = StreamSession::FrameOutputCallback;
    using StatusChangeCallback = StreamSession::StatusChangeCallback;
    using ErrorCallback = StreamSession::ErrorCallback;

    explicit StreamManager(size_t thread_pool_size = DEFAULT_THREAD_POOL_SIZE);
    ~StreamManager();

    // 禁止拷贝
    StreamManager(const StreamManager&) = delete;
    StreamManager& operator=(const StreamManager&) = delete;

    // 流管理
    std::string create_stream(const StreamConfig& config);
    bool remove_stream(const std::string& stream_id);
    std::shared_ptr<StreamSession> get_stream(const std::string& stream_id);

    // 批量操作
    bool start_stream(const std::string& stream_id);
    bool stop_stream(const std::string& stream_id);
    bool restart_stream(const std::string& stream_id);

    // 查询
    std::vector<std::string> list_stream_ids() const;
    size_t get_stream_count() const;
    size_t get_active_stream_count() const;

    // 全局回调设置（应用到所有流）
    void set_frame_output_callback(FrameOutputCallback callback);
    void set_status_change_callback(StatusChangeCallback callback);
    void set_error_callback(ErrorCallback callback);

    // 导出切片
    std::string export_clip(
        const std::string& stream_id,
        const std::string& event_id,
        uint32_t seconds_before = 5,
        uint32_t seconds_after = 5
    );

    // 全局指标
    struct GlobalMetrics {
        size_t total_streams;
        size_t active_streams;
        size_t thread_pool_size;
        size_t pending_tasks;
        uint64_t total_frames_decoded;
        uint64_t total_dropped_frames;
    };
    GlobalMetrics get_global_metrics() const;

private:
    void apply_callbacks(const std::shared_ptr<StreamSession>& session);

    std::unordered_map<std::string, std::shared_ptr<StreamSession>> streams_;
    mutable std::mutex streams_mutex_;

    std::unique_ptr<ThreadPool> thread_pool_;
    std::atomic<uint32_t> stream_counter_{0};

    // 全局回调
    FrameOutputCallback frame_output_callback_;
    StatusChangeCallback status_change_callback_;
    ErrorCallback error_callback_;
};

} // namespace campus_guard
