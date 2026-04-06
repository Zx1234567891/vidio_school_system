#include "stream_core/types.hpp"

extern "C" {
#include <libavutil/imgutils.h>
#include <libavutil/frame.h>
#include <libswscale/swscale.h>
}

#include <cstring>
#include <stdexcept>

namespace campus_guard {

// Frame 实现
Frame::Frame() = default;

Frame::~Frame() {
    release();
}

Frame::Frame(Frame&& other) noexcept {
    *this = std::move(other);
}

Frame& Frame::operator=(Frame&& other) noexcept {
    if (this != &other) {
        release();

        for (int i = 0; i < 4; ++i) {
            data_[i] = other.data_[i];
            stride_[i] = other.stride_[i];
            other.data_[i] = nullptr;
            other.stride_[i] = 0;
        }

        width_ = other.width_;
        height_ = other.height_;
        format_ = other.format_;
        timestamp_ = other.timestamp_;
        avframe_ref_ = other.avframe_ref_;

        other.width_ = 0;
        other.height_ = 0;
        other.avframe_ref_ = nullptr;
    }
    return *this;
}

void Frame::release() {
    if (avframe_ref_) {
        av_frame_free(&avframe_ref_);
    } else {
        // 手动释放数据
        for (int i = 0; i < 4; ++i) {
            if (data_[i]) {
                delete[] data_[i];
                data_[i] = nullptr;
            }
        }
    }
}

std::unique_ptr<Frame> Frame::from_avframe(AVFrame* avframe) {
    if (!avframe) {
        return nullptr;
    }

    auto frame = std::make_unique<Frame>();
    frame->width_ = avframe->width;
    frame->height_ = avframe->height;
    frame->timestamp_ = avframe->pts;

    // 分配 RGB 数据
    frame->format_ = PixelFormat::RGB24;
    size_t size = avframe->width * avframe->height * 3;
    frame->data_[0] = new uint8_t[size];
    frame->stride_[0] = avframe->width * 3;

    // 使用 sws_scale 转换格式
    SwsContext* sws_ctx = sws_getContext(
        avframe->width, avframe->height, static_cast<AVPixelFormat>(avframe->format),
        avframe->width, avframe->height, AV_PIX_FMT_RGB24,
        SWS_BILINEAR, nullptr, nullptr, nullptr
    );

    if (sws_ctx) {
        const uint8_t* src_data[4] = {
            avframe->data[0], avframe->data[1], avframe->data[2], avframe->data[3]
        };
        int src_linesize[4] = {
            avframe->linesize[0], avframe->linesize[1], avframe->linesize[2], avframe->linesize[3]
        };

        sws_scale(sws_ctx, src_data, src_linesize, 0, avframe->height,
                  &frame->data_[0], reinterpret_cast<int*>(&frame->stride_[0]));

        sws_freeContext(sws_ctx);
    }

    return frame;
}

bool Frame::allocate(int width, int height, PixelFormat format) {
    release();

    width_ = width;
    height_ = height;
    format_ = format;

    int channels = 0;
    switch (format) {
        case PixelFormat::RGB24:
        case PixelFormat::BGR24:
            channels = 3;
            break;
        case PixelFormat::RGBA:
        case PixelFormat::BGRA:
            channels = 4;
            break;
        default:
            return false;
    }

    size_t size = width * height * channels;
    data_[0] = new uint8_t[size]();
    stride_[0] = width * channels;

    return data_[0] != nullptr;
}

size_t Frame::size() const {
    int channels = 0;
    switch (format_) {
        case PixelFormat::RGB24:
        case PixelFormat::BGR24:
            channels = 3;
            break;
        case PixelFormat::RGBA:
        case PixelFormat::BGRA:
            channels = 4;
            break;
        default:
            return 0;
    }
    return width_ * height_ * channels;
}

std::unique_ptr<Frame> Frame::convert_to(PixelFormat target_format) const {
    // P1 简化实现，仅支持 RGB24 互转
    if (format_ == target_format) {
        auto copy = std::make_unique<Frame>();
        copy->allocate(width_, height_, target_format);
        std::memcpy(copy->data_[0], data_[0], size());
        copy->timestamp_ = timestamp_;
        return copy;
    }
    return nullptr;
}

// 工具函数
std::string status_to_string(StreamStatus status) {
    switch (status) {
        case StreamStatus::INIT: return "init";
        case StreamStatus::CONNECTING: return "connecting";
        case StreamStatus::RUNNING: return "running";
        case StreamStatus::DEGRADED: return "degraded";
        case StreamStatus::RECONNECTING: return "reconnecting";
        case StreamStatus::STOPPED: return "stopped";
        case StreamStatus::ERROR: return "error";
        default: return "unknown";
    }
}

std::string input_type_to_string(InputType type) {
    switch (type) {
        case InputType::RTSP: return "rtsp";
        case InputType::RTMP: return "rtmp";
        case InputType::FILE: return "file";
        default: return "unknown";
    }
}

std::string backpressure_to_string(BackpressureStrategy strategy) {
    switch (strategy) {
        case BackpressureStrategy::DROP_OLDEST: return "drop_oldest";
        case BackpressureStrategy::DROP_LATEST: return "drop_latest";
        case BackpressureStrategy::SKIP_FRAME: return "skip_frame";
        default: return "unknown";
    }
}

} // namespace campus_guard
