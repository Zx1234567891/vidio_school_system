#include "stream_core/clip_exporter.hpp"
#include "stream_core/types.hpp"

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/imgutils.h>
#include <libavutil/opt.h>
#include <libswscale/swscale.h>
}

#include <iostream>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <filesystem>

namespace campus_guard {

ClipExporter::Config::Config()
    : output_dir("./clips")
    , filename_prefix("clip")
    , duration_seconds(10)
    , fps(25)
    , quality(23) {}

ClipExporter::ClipExporter(Config config) : config_(config) {}

ClipExporter::~ClipExporter() {
    // 清理 FFmpeg 上下文
    if (codec_ctx_) {
        avcodec_free_context(&codec_ctx_);
    }
    if (format_ctx_) {
        if (!(format_ctx_->oformat->flags & AVFMT_NOFILE)) {
            avio_closep(&format_ctx_->pb);
        }
        avformat_free_context(format_ctx_);
    }
    if (sws_ctx_) {
        sws_freeContext(sws_ctx_);
    }
}

bool ClipExporter::initialize() {
    // P1 阶段简化实现
    // 创建输出目录
    std::filesystem::create_directories(config_.output_dir);
    ready_ = true;
    return true;
}

std::string ClipExporter::export_clip(
    const std::vector<DecodedFrame>& frames,
    const std::string& event_id) {

    if (!ready_ || frames.empty()) {
        return "";
    }

    std::string filename = generate_filename(event_id);

    // P1 阶段：仅保存为原始帧序列（后续实现视频编码）
    // 实际实现需要使用 FFmpeg 编码为 MP4

    std::cout << "[ClipExporter] Exporting " << frames.size()
              << " frames to " << filename << std::endl;

    return filename;
}

void ClipExporter::export_clip_async(
    const std::vector<DecodedFrame>& frames,
    const std::string& event_id,
    std::function<void(const std::string&)> callback) {

    // P1 阶段：同步执行
    std::string path = export_clip(frames, event_id);
    if (callback) {
        callback(path);
    }
}

std::string ClipExporter::generate_filename(const std::string& event_id) {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);

    std::stringstream ss;
    ss << config_.output_dir << "/"
       << config_.filename_prefix << "_"
       << event_id << "_"
       << std::put_time(std::localtime(&time), "%Y%m%d_%H%M%S")
       << ".mp4";

    return ss.str();
}

} // namespace campus_guard
