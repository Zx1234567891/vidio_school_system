#pragma once

#include <cstdint>
#include <string>
#include <chrono>
#include <vector>
#include <memory>

// FFmpeg 前向声明
struct AVFrame;
struct AVPacket;
struct AVCodecContext;
struct AVFormatContext;

namespace campus_guard {

/**
 * 流状态枚举
 */
enum class StreamStatus {
    INIT,
    CONNECTING,
    RUNNING,
    DEGRADED,
    RECONNECTING,
    STOPPED,
    ERROR
};

/**
 * 输入类型
 */
enum class InputType {
    RTSP,
    RTMP,
    FILE
};

/**
 * 背压策略
 */
enum class BackpressureStrategy {
    DROP_OLDEST,    // 丢弃最旧的帧
    DROP_LATEST,    // 丢弃最新的帧
    SKIP_FRAME      // 跳帧（每N帧处理1帧）
};

/**
 * 流配置
 */
struct StreamConfig {
    std::string id;
    std::string name;
    InputType input_type;
    std::string url;
    bool enabled = true;

    // 队列配置
    uint32_t max_queue_size = 100;           // 有界队列容量
    BackpressureStrategy backpressure = BackpressureStrategy::DROP_OLDEST;

    // 环形缓冲区配置
    uint32_t ring_buffer_seconds = 30;       // 保留最近30秒

    // 重连配置
    uint32_t max_reconnect_attempts = 5;     // 最大重连次数
    uint32_t reconnect_interval_ms = 3000;   // 重连间隔

    // 解码配置
    uint32_t target_fps = 25;                // 目标帧率
    uint32_t width = 1920;                   // 目标宽度
    uint32_t height = 1080;                  // 目标高度
};

/**
 * 流指标
 */
struct StreamMetrics {
    double fps = 0.0;
    size_t queue_depth = 0;
    uint64_t dropped_frames = 0;
    double decode_latency_ms = 0.0;
    uint32_t reconnect_count = 0;
    std::chrono::seconds uptime{0};

    // 扩展指标
    uint64_t total_frames_decoded = 0;
    uint64_t total_bytes_received = 0;
    double bitrate_kbps = 0.0;
};

/**
 * 像素格式
 */
enum class PixelFormat {
    RGB24,
    BGR24,
    RGBA,
    BGRA,
    YUV420P,
    NV12
};

/**
 * 帧数据结构
 *
 * 封装 AVFrame，提供 RAII 内存管理
 */
class Frame {
public:
    Frame();
    ~Frame();

    // 禁止拷贝，允许移动
    Frame(const Frame&) = delete;
    Frame& operator=(const Frame&) = delete;
    Frame(Frame&& other) noexcept;
    Frame& operator=(Frame&& other) noexcept;

    // 从 AVFrame 构造
    static std::unique_ptr<Frame> from_avframe(AVFrame* avframe);

    // 分配空帧
    bool allocate(int width, int height, PixelFormat format);

    // 数据访问
    uint8_t* data(size_t plane = 0) { return data_[plane]; }
    const uint8_t* data(size_t plane = 0) const { return data_[plane]; }
    size_t stride(size_t plane = 0) const { return stride_[plane]; }

    // 属性
    int width() const { return width_; }
    int height() const { return height_; }
    PixelFormat format() const { return format_; }
    int64_t timestamp() const { return timestamp_; }
    void set_timestamp(int64_t ts) { timestamp_ = ts; }

    // 计算帧大小
    size_t size() const;

    // 转换为指定格式
    std::unique_ptr<Frame> convert_to(PixelFormat target_format) const;

private:
    void release();

    uint8_t* data_[4] = {nullptr, nullptr, nullptr, nullptr};
    size_t stride_[4] = {0, 0, 0, 0};
    int width_ = 0;
    int height_ = 0;
    PixelFormat format_ = PixelFormat::RGB24;
    int64_t timestamp_ = 0;

    // AVFrame 引用（如果由 AVFrame 构造）
    AVFrame* avframe_ref_ = nullptr;
};

/**
 * 解码后的帧数据（用于队列传输）
 */
struct DecodedFrame {
    std::shared_ptr<Frame> frame;
    int64_t pts;                    // 显示时间戳
    int64_t dts;                    // 解码时间戳
    double timestamp_ms;            // 毫秒时间戳
    bool key_frame;                 // 是否关键帧

    DecodedFrame() = default;
    DecodedFrame(DecodedFrame&&) = default;
    DecodedFrame& operator=(DecodedFrame&&) = default;

    // 浅拷贝（共享 Frame）
    DecodedFrame(const DecodedFrame& other) = default;
    DecodedFrame& operator=(const DecodedFrame& other) = default;
};

std::string status_to_string(StreamStatus status);
std::string input_type_to_string(InputType type);
std::string backpressure_to_string(BackpressureStrategy strategy);

} // namespace campus_guard
