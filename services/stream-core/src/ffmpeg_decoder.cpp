#include "stream_core/ffmpeg_decoder.hpp"
#include "stream_core/types.hpp"

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/imgutils.h>
#include <libavutil/time.h>
#include <libswscale/swscale.h>
}

#include <iostream>
#include <thread>

namespace campus_guard {

FFmpegDecoder::FFmpegDecoder() = default;

FFmpegDecoder::~FFmpegDecoder() {
    stop_decode_loop();
    close();
}

bool FFmpegDecoder::open(const std::string& url, InputType input_type) {
    url_ = url;
    input_type_ = input_type;

    // 分配格式上下文
    format_ctx_ = avformat_alloc_context();
    if (!format_ctx_) {
        last_error_ = "Failed to allocate format context";
        return false;
    }

    // 设置 RTSP 选项
    AVDictionary* opts = nullptr;
    if (input_type == InputType::RTSP) {
        av_dict_set(&opts, "rtsp_transport", "tcp", 0);
        av_dict_set(&opts, "stimeout", "5000000", 0);  // 5秒超时
    }

    // 打开输入
    int ret = avformat_open_input(&format_ctx_, url.c_str(), nullptr, &opts);
    av_dict_free(&opts);

    if (ret < 0) {
        char errbuf[256];
        av_strerror(ret, errbuf, sizeof(errbuf));
        last_error_ = std::string("Failed to open input: ") + errbuf;
        return false;
    }

    // 获取流信息
    ret = avformat_find_stream_info(format_ctx_, nullptr);
    if (ret < 0) {
        char errbuf[256];
        av_strerror(ret, errbuf, sizeof(errbuf));
        last_error_ = std::string("Failed to find stream info: ") + errbuf;
        return false;
    }

    // 查找视频流
    video_stream_index_ = -1;
    for (unsigned int i = 0; i < format_ctx_->nb_streams; i++) {
        if (format_ctx_->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            video_stream_index_ = i;
            break;
        }
    }

    if (video_stream_index_ == -1) {
        last_error_ = "No video stream found";
        return false;
    }

    // 初始化编解码器
    if (!init_codec()) {
        return false;
    }

    // 获取流信息
    AVStream* stream = format_ctx_->streams[video_stream_index_];
    width_ = codec_ctx_->width;
    height_ = codec_ctx_->height;
    fps_ = av_q2d(stream->avg_frame_rate);
    bitrate_ = stream->codecpar->bit_rate;

    // 分配帧和包
    frame_ = av_frame_alloc();
    packet_ = av_packet_alloc();

    if (!frame_ || !packet_) {
        last_error_ = "Failed to allocate frame/packet";
        return false;
    }

    return true;
}

bool FFmpegDecoder::init_codec() {
    AVStream* stream = format_ctx_->streams[video_stream_index_];
    const AVCodec* codec = avcodec_find_decoder(stream->codecpar->codec_id);

    if (!codec) {
        last_error_ = "Codec not found";
        return false;
    }

    codec_ctx_ = avcodec_alloc_context3(codec);
    if (!codec_ctx_) {
        last_error_ = "Failed to allocate codec context";
        return false;
    }

    int ret = avcodec_parameters_to_context(codec_ctx_, stream->codecpar);
    if (ret < 0) {
        last_error_ = "Failed to copy codec parameters";
        return false;
    }

    ret = avcodec_open2(codec_ctx_, codec, nullptr);
    if (ret < 0) {
        char errbuf[256];
        av_strerror(ret, errbuf, sizeof(errbuf));
        last_error_ = std::string("Failed to open codec: ") + errbuf;
        return false;
    }

    return true;
}

void FFmpegDecoder::close() {
    stop_decode_loop();
    cleanup();
}

void FFmpegDecoder::cleanup() {
    if (sws_ctx_) {
        sws_freeContext(sws_ctx_);
        sws_ctx_ = nullptr;
    }
    if (frame_) {
        av_frame_free(&frame_);
    }
    if (packet_) {
        av_packet_free(&packet_);
    }
    if (codec_ctx_) {
        avcodec_free_context(&codec_ctx_);
    }
    if (format_ctx_) {
        avformat_close_input(&format_ctx_);
        avformat_free_context(format_ctx_);
        format_ctx_ = nullptr;
    }
}

bool FFmpegDecoder::read_frame(int timeout_ms) {
    if (!format_ctx_ || !codec_ctx_) {
        return false;
    }

    int ret = av_read_frame(format_ctx_, packet_);
    if (ret < 0) {
        if (ret == AVERROR_EOF) {
            return false;  // 文件结束
        }
        char errbuf[256];
        av_strerror(ret, errbuf, sizeof(errbuf));
        last_error_ = std::string("Read frame error: ") + errbuf;
        return false;
    }

    if (packet_->stream_index == video_stream_index_) {
        decode_packet(packet_);
    }

    av_packet_unref(packet_);
    return true;
}

bool FFmpegDecoder::decode_packet(AVPacket* packet) {
    int ret = avcodec_send_packet(codec_ctx_, packet);
    if (ret < 0) {
        return false;
    }

    while (ret >= 0) {
        ret = avcodec_receive_frame(codec_ctx_, frame_);
        if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
            break;
        }
        if (ret < 0) {
            return false;
        }

        // 转换为 RGB
        if (!sws_ctx_) {
            sws_ctx_ = sws_getContext(
                frame_->width, frame_->height, static_cast<AVPixelFormat>(frame_->format),
                frame_->width, frame_->height, AV_PIX_FMT_RGB24,
                SWS_BILINEAR, nullptr, nullptr, nullptr
            );
        }

        // 创建 DecodedFrame
        auto decoded = std::make_unique<DecodedFrame>();
        decoded->frame = Frame::from_avframe(frame_);
        if (decoded->frame) {
            decoded->pts = frame_->pts;
            decoded->dts = frame_->pkt_dts;
            decoded->timestamp_ms = frame_->pts * av_q2d(format_ctx_->streams[video_stream_index_]->time_base) * 1000;
            decoded->key_frame = (frame_->flags & AV_FRAME_FLAG_KEY) != 0;

            if (frame_callback_) {
                frame_callback_(std::move(decoded));
            }
        }
    }

    return true;
}

void FFmpegDecoder::start_decode_loop() {
    if (running_.exchange(true)) {
        return;  // 已经在运行
    }

    should_stop_ = false;
    decode_thread_ = std::thread(&FFmpegDecoder::decode_loop, this);
}

void FFmpegDecoder::stop_decode_loop() {
    should_stop_ = true;
    running_ = false;

    if (decode_thread_.joinable()) {
        decode_thread_.join();
    }
}

void FFmpegDecoder::decode_loop() {
    while (!should_stop_) {
        if (!read_frame(100)) {
            if (!should_stop_ && error_callback_) {
                error_callback_(last_error_);
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }
}

} // namespace campus_guard
