#include "stream_core/c_api.hpp"
#include "stream_core/stream_manager.hpp"
#include "stream_core/stream_session.hpp"

#include <cstring>
#include <string>
#include <vector>
#include <memory>

using namespace campus_guard;

// 内部结构包装
struct CGStreamManagerWrapper {
    std::unique_ptr<StreamManager> manager;

    // 回调存储（防止被垃圾回收）
    CGFrameCallback frame_callback = nullptr;
    CGStatusCallback status_callback = nullptr;
    CGErrorCallback error_callback = nullptr;
    void* frame_user_data = nullptr;
    void* status_user_data = nullptr;
    void* error_user_data = nullptr;
};

// 版本信息
static const char* VERSION = "0.1.0";

const char* cg_version() {
    return VERSION;
}

const char* cg_error_string(CGErrorCode code) {
    switch (code) {
        case CG_OK: return "Success";
        case CG_ERROR_INVALID_HANDLE: return "Invalid handle";
        case CG_ERROR_INVALID_PARAM: return "Invalid parameter";
        case CG_ERROR_OUT_OF_MEMORY: return "Out of memory";
        case CG_ERROR_STREAM_NOT_FOUND: return "Stream not found";
        case CG_ERROR_STREAM_LIMIT_EXCEEDED: return "Stream limit exceeded";
        case CG_ERROR_FFMPEG_ERROR: return "FFmpeg error";
        case CG_ERROR_UNKNOWN: return "Unknown error";
        default: return "Unknown error code";
    }
}

// 辅助函数：转换状态
static CGStreamStatus to_c_status(StreamStatus status) {
    switch (status) {
        case StreamStatus::INIT: return CG_STATUS_INIT;
        case StreamStatus::CONNECTING: return CG_STATUS_CONNECTING;
        case StreamStatus::RUNNING: return CG_STATUS_RUNNING;
        case StreamStatus::DEGRADED: return CG_STATUS_DEGRADED;
        case StreamStatus::RECONNECTING: return CG_STATUS_RECONNECTING;
        case StreamStatus::STOPPED: return CG_STATUS_STOPPED;
        case StreamStatus::ERROR: return CG_STATUS_ERROR;
        default: return CG_STATUS_ERROR;
    }
}

// 辅助函数：转换输入类型
static InputType from_c_input_type(CGInputType type) {
    switch (type) {
        case CG_INPUT_RTSP: return InputType::RTSP;
        case CG_INPUT_RTMP: return InputType::RTMP;
        case CG_INPUT_FILE: return InputType::FILE;
        default: return InputType::FILE;
    }
}

CGStreamManagerHandle cg_stream_manager_create(uint32_t max_streams, uint32_t thread_pool_size) {
    auto wrapper = new CGStreamManagerWrapper();
    wrapper->manager = std::make_unique<StreamManager>(thread_pool_size);
    return wrapper;
}

void cg_stream_manager_destroy(CGStreamManagerHandle handle) {
    if (!handle) return;
    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);
    delete wrapper;
}

CGErrorCode cg_stream_create(CGStreamManagerHandle handle, const CGStreamConfig* config, char* stream_id_out) {
    if (!handle || !config || !stream_id_out) {
        return CG_ERROR_INVALID_PARAM;
    }

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);

    try {
        StreamConfig stream_config;
        stream_config.name = config->name ? config->name : "";
        stream_config.input_type = from_c_input_type(config->input_type);
        stream_config.url = config->url ? config->url : "";
        stream_config.enabled = config->enabled != 0;
        stream_config.max_queue_size = config->max_queue_size;
        stream_config.ring_buffer_seconds = config->ring_buffer_seconds;
        stream_config.max_reconnect_attempts = config->max_reconnect_attempts;
        stream_config.reconnect_interval_ms = config->reconnect_interval_ms;

        std::string id = wrapper->manager->create_stream(stream_config);
        std::strncpy(stream_id_out, id.c_str(), 31);
        stream_id_out[31] = '\0';

        return CG_OK;
    } catch (const std::exception& e) {
        if (std::string(e.what()).find("Maximum number of streams") != std::string::npos) {
            return CG_ERROR_STREAM_LIMIT_EXCEEDED;
        }
        return CG_ERROR_UNKNOWN;
    }
}

CGErrorCode cg_stream_destroy(CGStreamManagerHandle handle, const char* stream_id) {
    if (!handle || !stream_id) {
        return CG_ERROR_INVALID_PARAM;
    }

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);

    if (wrapper->manager->remove_stream(stream_id)) {
        return CG_OK;
    }
    return CG_ERROR_STREAM_NOT_FOUND;
}

CGErrorCode cg_stream_start(CGStreamManagerHandle handle, const char* stream_id) {
    if (!handle || !stream_id) {
        return CG_ERROR_INVALID_PARAM;
    }

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);

    if (wrapper->manager->start_stream(stream_id)) {
        return CG_OK;
    }
    return CG_ERROR_STREAM_NOT_FOUND;
}

CGErrorCode cg_stream_stop(CGStreamManagerHandle handle, const char* stream_id) {
    if (!handle || !stream_id) {
        return CG_ERROR_INVALID_PARAM;
    }

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);

    if (wrapper->manager->stop_stream(stream_id)) {
        return CG_OK;
    }
    return CG_ERROR_STREAM_NOT_FOUND;
}

CGErrorCode cg_stream_restart(CGStreamManagerHandle handle, const char* stream_id) {
    if (!handle || !stream_id) {
        return CG_ERROR_INVALID_PARAM;
    }

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);

    if (wrapper->manager->restart_stream(stream_id)) {
        return CG_OK;
    }
    return CG_ERROR_STREAM_NOT_FOUND;
}

CGStreamStatus cg_stream_get_status(CGStreamManagerHandle handle, const char* stream_id) {
    if (!handle || !stream_id) {
        return CG_STATUS_ERROR;
    }

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);
    auto session = wrapper->manager->get_stream(stream_id);

    if (!session) {
        return CG_STATUS_ERROR;
    }

    return to_c_status(session->get_status());
}

CGErrorCode cg_stream_get_metrics(CGStreamManagerHandle handle, const char* stream_id, CGStreamMetrics* metrics_out) {
    if (!handle || !stream_id || !metrics_out) {
        return CG_ERROR_INVALID_PARAM;
    }

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);
    auto session = wrapper->manager->get_stream(stream_id);

    if (!session) {
        return CG_ERROR_STREAM_NOT_FOUND;
    }

    auto metrics = session->get_metrics();
    metrics_out->fps = metrics.fps;
    metrics_out->queue_depth = metrics.queue_depth;
    metrics_out->dropped_frames = metrics.dropped_frames;
    metrics_out->decode_latency_ms = metrics.decode_latency_ms;
    metrics_out->reconnect_count = metrics.reconnect_count;
    metrics_out->uptime_seconds = metrics.uptime.count();
    metrics_out->total_frames_decoded = metrics.total_frames_decoded;
    metrics_out->total_bytes_received = metrics.total_bytes_received;
    metrics_out->bitrate_kbps = metrics.bitrate_kbps;

    return CG_OK;
}

CGErrorCode cg_stream_list(CGStreamManagerHandle handle, char* stream_ids, size_t buffer_size, uint32_t* count_out) {
    if (!handle || !stream_ids || buffer_size == 0) {
        return CG_ERROR_INVALID_PARAM;
    }

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);
    auto ids = wrapper->manager->list_stream_ids();

    if (count_out) {
        *count_out = static_cast<uint32_t>(ids.size());
    }

    // 将 ID 列表以 '\0' 分隔写入缓冲区
    size_t pos = 0;
    for (size_t i = 0; i < ids.size(); ++i) {
        const auto& id = ids[i];
        if (pos + id.length() + 1 >= buffer_size) {
            break;  // 缓冲区已满
        }

        std::memcpy(stream_ids + pos, id.c_str(), id.length());
        pos += id.length();
        stream_ids[pos++] = '\0';
    }

    // 以双 '\0' 结束
    if (pos < buffer_size) {
        stream_ids[pos] = '\0';
    }

    return CG_OK;
}

void cg_set_frame_callback(CGStreamManagerHandle handle, CGFrameCallback callback, void* user_data) {
    if (!handle) return;

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);
    wrapper->frame_callback = callback;
    wrapper->frame_user_data = user_data;

    // 设置 C++ 回调
    if (callback) {
        wrapper->manager->set_frame_output_callback(
            [callback, user_data](const std::string& stream_id, std::unique_ptr<DecodedFrame> frame) {
                // P1 简化：不实际传递帧数据，仅传递元信息
                callback(stream_id.c_str(), nullptr, 0, 0, 0, 0, user_data);
            }
        );
    } else {
        wrapper->manager->set_frame_output_callback(nullptr);
    }
}

void cg_set_status_callback(CGStreamManagerHandle handle, CGStatusCallback callback, void* user_data) {
    if (!handle) return;

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);
    wrapper->status_callback = callback;
    wrapper->status_user_data = user_data;

    if (callback) {
        wrapper->manager->set_status_change_callback(
            [callback, user_data](const std::string& stream_id, StreamStatus new_status, StreamStatus oldStatus) {
                callback(stream_id.c_str(), to_c_status(new_status), to_c_status(oldStatus), user_data);
            }
        );
    } else {
        wrapper->manager->set_status_change_callback(nullptr);
    }
}

void cg_set_error_callback(CGStreamManagerHandle handle, CGErrorCallback callback, void* user_data) {
    if (!handle) return;

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);
    wrapper->error_callback = callback;
    wrapper->error_user_data = user_data;

    if (callback) {
        wrapper->manager->set_error_callback(
            [callback, user_data](const std::string& stream_id, const std::string& error) {
                callback(stream_id.c_str(), -1, error.c_str(), user_data);
            }
        );
    } else {
        wrapper->manager->set_error_callback(nullptr);
    }
}

CGErrorCode cg_export_clip(CGStreamManagerHandle handle, const char* stream_id, const char* event_id,
                           uint32_t seconds_before, uint32_t seconds_after,
                           char* output_path_out, size_t buffer_size) {
    if (!handle || !stream_id || !event_id || !output_path_out || buffer_size == 0) {
        return CG_ERROR_INVALID_PARAM;
    }

    auto wrapper = static_cast<CGStreamManagerWrapper*>(handle);
    std::string path = wrapper->manager->export_clip(stream_id, event_id, seconds_before, seconds_after);

    if (path.empty()) {
        return CG_ERROR_STREAM_NOT_FOUND;
    }

    std::strncpy(output_path_out, path.c_str(), buffer_size - 1);
    output_path_out[buffer_size - 1] = '\0';

    return CG_OK;
}
