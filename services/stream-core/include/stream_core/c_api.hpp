#pragma once

#include <cstdint>
#include <cstddef>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Campus Guard Stream Core C API
 *
 * 供 Python 等语言通过 ctypes/ffi 调用
 */

//  opaque handle 类型
typedef void* CGStreamManagerHandle;
typedef void* CGStreamHandle;

// 错误码
typedef enum {
    CG_OK = 0,
    CG_ERROR_INVALID_HANDLE = -1,
    CG_ERROR_INVALID_PARAM = -2,
    CG_ERROR_OUT_OF_MEMORY = -3,
    CG_ERROR_STREAM_NOT_FOUND = -4,
    CG_ERROR_STREAM_LIMIT_EXCEEDED = -5,
    CG_ERROR_FFMPEG_ERROR = -6,
    CG_ERROR_UNKNOWN = -99
} CGErrorCode;

// 流状态
typedef enum {
    CG_STATUS_INIT = 0,
    CG_STATUS_CONNECTING = 1,
    CG_STATUS_RUNNING = 2,
    CG_STATUS_DEGRADED = 3,
    CG_STATUS_RECONNECTING = 4,
    CG_STATUS_STOPPED = 5,
    CG_STATUS_ERROR = 6
} CGStreamStatus;

// 输入类型
typedef enum {
    CG_INPUT_RTSP = 0,
    CG_INPUT_RTMP = 1,
    CG_INPUT_FILE = 2
} CGInputType;

// 流配置
typedef struct {
    const char* name;
    CGInputType input_type;
    const char* url;
    int enabled;
    uint32_t max_queue_size;
    uint32_t ring_buffer_seconds;
    uint32_t max_reconnect_attempts;
    uint32_t reconnect_interval_ms;
} CGStreamConfig;

// 流指标
typedef struct {
    double fps;
    size_t queue_depth;
    uint64_t dropped_frames;
    double decode_latency_ms;
    uint32_t reconnect_count;
    uint64_t uptime_seconds;
    uint64_t total_frames_decoded;
    uint64_t total_bytes_received;
    double bitrate_kbps;
} CGStreamMetrics;

// 帧数据回调
typedef void (*CGFrameCallback)(
    const char* stream_id,
    const uint8_t* data,
    size_t data_size,
    int width,
    int height,
    int64_t timestamp_ms,
    void* user_data
);

// 状态变更回调
typedef void (*CGStatusCallback)(
    const char* stream_id,
    CGStreamStatus new_status,
    CGStreamStatus old_status,
    void* user_data
);

// 错误回调
typedef void (*CGErrorCallback)(
    const char* stream_id,
    int error_code,
    const char* error_message,
    void* user_data
);

/**
 * 创建流管理器
 * @param max_streams 最大流数（默认20）
 * @param thread_pool_size 线程池大小（默认8）
 * @return 管理器句柄，失败返回 NULL
 */
CGStreamManagerHandle cg_stream_manager_create(
    uint32_t max_streams,
    uint32_t thread_pool_size
);

/**
 * 销毁流管理器
 */
void cg_stream_manager_destroy(CGStreamManagerHandle handle);

/**
 * 创建流
 * @param handle 管理器句柄
 * @param config 流配置
 * @param stream_id_out 输出流ID缓冲区（至少32字节）
 * @return 错误码
 */
CGErrorCode cg_stream_create(
    CGStreamManagerHandle handle,
    const CGStreamConfig* config,
    char* stream_id_out
);

/**
 * 删除流
 */
CGErrorCode cg_stream_destroy(
    CGStreamManagerHandle handle,
    const char* stream_id
);

/**
 * 启动流
 */
CGErrorCode cg_stream_start(
    CGStreamManagerHandle handle,
    const char* stream_id
);

/**
 * 停止流
 */
CGErrorCode cg_stream_stop(
    CGStreamManagerHandle handle,
    const char* stream_id
);

/**
 * 重启流
 */
CGErrorCode cg_stream_restart(
    CGStreamManagerHandle handle,
    const char* stream_id
);

/**
 * 获取流状态
 */
CGStreamStatus cg_stream_get_status(
    CGStreamManagerHandle handle,
    const char* stream_id
);

/**
 * 获取流指标
 */
CGErrorCode cg_stream_get_metrics(
    CGStreamManagerHandle handle,
    const char* stream_id,
    CGStreamMetrics* metrics_out
);

/**
 * 列出所有流ID
 * @param stream_ids 输出缓冲区（以 '\0' 分隔的字符串）
 * @param buffer_size 缓冲区大小
 * @param count_out 输出流数量
 */
CGErrorCode cg_stream_list(
    CGStreamManagerHandle handle,
    char* stream_ids,
    size_t buffer_size,
    uint32_t* count_out
);

/**
 * 设置帧回调
 * @param handle 管理器句柄
 * @param callback 回调函数
 * @param user_data 用户数据（会传递给回调）
 */
void cg_set_frame_callback(
    CGStreamManagerHandle handle,
    CGFrameCallback callback,
    void* user_data
);

/**
 * 设置状态回调
 */
void cg_set_status_callback(
    CGStreamManagerHandle handle,
    CGStatusCallback callback,
    void* user_data
);

/**
 * 设置错误回调
 */
void cg_set_error_callback(
    CGStreamManagerHandle handle,
    CGErrorCallback callback,
    void* user_data
);

/**
 * 导出切片
 * @param handle 管理器句柄
 * @param stream_id 流ID
 * @param event_id 事件ID（用于生成文件名）
 * @param seconds_before 事件前秒数
 * @param seconds_after 事件后秒数
 * @param output_path_out 输出文件路径缓冲区
 * @param buffer_size 缓冲区大小
 * @return 错误码
 */
CGErrorCode cg_export_clip(
    CGStreamManagerHandle handle,
    const char* stream_id,
    const char* event_id,
    uint32_t seconds_before,
    uint32_t seconds_after,
    char* output_path_out,
    size_t buffer_size
);

/**
 * 获取错误字符串
 */
const char* cg_error_string(CGErrorCode code);

/**
 * 获取版本信息
 */
const char* cg_version();

#ifdef __cplusplus
}
#endif
