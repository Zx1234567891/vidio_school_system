#pragma once

#include "stream_core/types.hpp"
#include <string>
#include <functional>
#include <thread>

// FFmpeg 前向声明
struct AVFormatContext;
struct AVCodecContext;
struct AVCodec;
struct AVFrame;
struct AVPacket;
struct SwsContext;

namespace campus_guard {

/**
 * FFmpeg 解码器
 *
 * 封装 FFmpeg 解码功能，支持 RTSP/RTMP/文件输入
 */
class FFmpegDecoder {
public:
    // 帧回调函数类型
    using FrameCallback = std::function<void(std::unique_ptr<DecodedFrame>)>;
    // 错误回调函数类型
    using ErrorCallback = std::function<void(const std::string&)>;

    FFmpegDecoder();
    ~FFmpegDecoder();

    // 禁止拷贝
    FFmpegDecoder(const FFmpegDecoder&) = delete;
    FFmpegDecoder& operator=(const FFmpegDecoder&) = delete;

    /**
     * 打开输入源
     * @param url 输入 URL (rtsp://, rtmp://, file://)
     * @param input_type 输入类型
     * @return 是否成功
     */
    bool open(const std::string& url, InputType input_type);

    /**
     * 关闭输入源
     */
    void close();

    /**
     * 读取并解码一帧
     * @param timeout_ms 超时时间（毫秒）
     * @return 是否成功读取到帧
     */
    bool read_frame(int timeout_ms = 1000);

    /**
     * 开始解码循环（在单独线程中运行）
     */
    void start_decode_loop();

    /**
     * 停止解码循环
     */
    void stop_decode_loop();

    /**
     * 设置帧回调
     */
    void set_frame_callback(FrameCallback callback) { frame_callback_ = callback; }

    /**
     * 设置错误回调
     */
    void set_error_callback(ErrorCallback callback) { error_callback_ = callback; }

    /**
     * 获取流信息
     */
    int get_width() const { return width_; }
    int get_height() const { return height_; }
    double get_fps() const { return fps_; }
    int64_t get_bitrate() const { return bitrate_; }

    /**
     * 是否正在运行
     */
    bool is_running() const { return running_.load(); }

    /**
     * 获取最后错误
     */
    std::string get_last_error() const { return last_error_; }

private:
    bool init_codec();
    void cleanup();
    bool decode_packet(AVPacket* packet);
    void decode_loop();

    // FFmpeg 上下文
    AVFormatContext* format_ctx_ = nullptr;
    AVCodecContext* codec_ctx_ = nullptr;
    const AVCodec* codec_ = nullptr;
    AVFrame* frame_ = nullptr;
    AVPacket* packet_ = nullptr;
    SwsContext* sws_ctx_ = nullptr;

    // 流索引
    int video_stream_index_ = -1;

    // 流信息
    int width_ = 0;
    int height_ = 0;
    double fps_ = 0.0;
    int64_t bitrate_ = 0;

    // 回调
    FrameCallback frame_callback_;
    ErrorCallback error_callback_;

    // 状态
    std::atomic<bool> running_{false};
    std::atomic<bool> should_stop_{false};
    std::string last_error_;

    // 解码线程
    std::thread decode_thread_;

    // 输入信息
    std::string url_;
    InputType input_type_;
};

} // namespace campus_guard
