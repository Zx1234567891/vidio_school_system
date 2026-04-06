#pragma once

#include "stream_core/types.hpp"
#include <string>
#include <functional>
#include <atomic>
#include <fstream>

// FFmpeg 前向声明
struct AVFormatContext;
struct AVCodecContext;
struct AVStream;
struct SwsContext;

namespace campus_guard {

/**
 * 切片导出器
 *
 * 将环形缓冲区中的帧导出为视频文件
 */
class ClipExporter {
public:
    struct Config {
        Config();
        std::string output_dir;          // 输出目录
        std::string filename_prefix;     // 文件名前缀
        uint32_t duration_seconds;       // 默认导出时长
        uint32_t fps;                    // 输出帧率
        uint32_t quality;                // 编码质量 (0-51, 越小越好)
    };

    explicit ClipExporter(Config config = {});
    ~ClipExporter();

    // 禁止拷贝
    ClipExporter(const ClipExporter&) = delete;
    ClipExporter& operator=(const ClipExporter&) = delete;

    /**
     * 初始化导出器
     */
    bool initialize();

    /**
     * 导出切片
     * @param frames 要导出的帧 (DecodedFrame vector)
     * @param event_id 关联的事件ID
     * @return 导出的文件路径
     */
    std::string export_clip(
        const std::vector<DecodedFrame>& frames,
        const std::string& event_id
    );

    /**
     * 开始异步导出
     */
    void export_clip_async(
        const std::vector<DecodedFrame>& frames,
        const std::string& event_id,
        std::function<void(const std::string&)> callback
    );

    /**
     * 获取导出器状态
     */
    bool is_ready() const { return ready_.load(); }

    /**
     * 获取最后错误
     */
    std::string get_last_error() const { return last_error_; }

private:
    bool encode_frame(const Frame& frame);
    std::string generate_filename(const std::string& event_id);

    Config config_;
    std::atomic<bool> ready_{false};
    std::string last_error_;

    // FFmpeg 编码上下文
    AVFormatContext* format_ctx_ = nullptr;
    AVCodecContext* codec_ctx_ = nullptr;
    AVStream* video_stream_ = nullptr;
    SwsContext* sws_ctx_ = nullptr;
    int64_t next_pts_ = 0;
};

} // namespace campus_guard
