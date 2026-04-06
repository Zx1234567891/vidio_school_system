#include "stream_core/stream_manager.hpp"
#include "stream_core/types.hpp"

#include <iostream>
#include <chrono>
#include <thread>
#include <csignal>

using namespace campus_guard;

static std::atomic<bool> g_running{true};

void signal_handler(int sig) {
    std::cout << "\n[Main] Received signal " << sig << ", shutting down..." << std::endl;
    g_running = false;
}

void print_metrics(StreamManager& manager) {
    auto global = manager.get_global_metrics();

    std::cout << "\n========== Global Metrics ==========" << std::endl;
    std::cout << "Total streams: " << global.total_streams << std::endl;
    std::cout << "Active streams: " << global.active_streams << std::endl;
    std::cout << "Thread pool size: " << global.thread_pool_size << std::endl;
    std::cout << "Pending tasks: " << global.pending_tasks << std::endl;
    std::cout << "Total frames decoded: " << global.total_frames_decoded << std::endl;
    std::cout << "Total dropped frames: " << global.total_dropped_frames << std::endl;

    // 打印每个流的指标
    auto ids = manager.list_stream_ids();
    for (const auto& id : ids) {
        auto session = manager.get_stream(id);
        if (session) {
            auto m = session->get_metrics();
            std::cout << "\n--- Stream: " << id << " ---" << std::endl;
            std::cout << "  Status: " << status_to_string(session->get_status()) << std::endl;
            std::cout << "  FPS: " << m.fps << std::endl;
            std::cout << "  Queue depth: " << m.queue_depth << std::endl;
            std::cout << "  Dropped frames: " << m.dropped_frames << std::endl;
            std::cout << "  Decode latency: " << m.decode_latency_ms << " ms" << std::endl;
            std::cout << "  Reconnect count: " << m.reconnect_count << std::endl;
            std::cout << "  Uptime: " << m.uptime.count() << " s" << std::endl;
            std::cout << "  Total frames: " << m.total_frames_decoded << std::endl;
            std::cout << "  Bitrate: " << m.bitrate_kbps << " kbps" << std::endl;
        }
    }
    std::cout << "====================================\n" << std::endl;
}

int main(int argc, char* argv[]) {
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    std::cout << "========================================" << std::endl;
    std::cout << "Campus Guard Stream Core" << std::endl;
    std::cout << "Version 0.1.0 (P1 - FFmpeg Edition)" << std::endl;
    std::cout << "========================================" << std::endl;

    try {
        // 创建流管理器
        StreamManager manager(8);

        // 设置全局回调
        manager.set_status_change_callback([](const std::string& id, StreamStatus new_status, StreamStatus old_status) {
            std::cout << "[Callback] Stream " << id << " status changed: "
                      << status_to_string(old_status) << " -> " << status_to_string(new_status) << std::endl;
        });

        manager.set_error_callback([](const std::string& id, const std::string& error) {
            std::cerr << "[Callback] Stream " << id << " error: " << error << std::endl;
        });

        std::cout << "\n[Main] Creating test streams..." << std::endl;

        // 创建测试流
        // 注意：这里使用测试文件路径，实际使用时需要替换为真实的 RTSP URL 或视频文件
        std::vector<std::string> test_urls = {
            "test_video_1.mp4",
            "test_video_2.mp4",
            "test_video_3.mp4"
        };

        std::vector<std::string> stream_ids;

        for (size_t i = 0; i < test_urls.size(); ++i) {
            StreamConfig config;
            config.name = "Test Stream " + std::to_string(i + 1);
            config.input_type = InputType::FILE;
            config.url = test_urls[i];
            config.max_queue_size = 50;
            config.ring_buffer_seconds = 10;
            config.max_reconnect_attempts = 3;
            config.reconnect_interval_ms = 2000;

            std::string id = manager.create_stream(config);
            stream_ids.push_back(id);
            std::cout << "  Created: " << id << " -> " << test_urls[i] << std::endl;
        }

        std::cout << "\n[Main] Starting streams..." << std::endl;

        // 启动所有流
        for (const auto& id : stream_ids) {
            if (manager.start_stream(id)) {
                std::cout << "  Started: " << id << std::endl;
            } else {
                std::cerr << "  Failed to start: " << id << std::endl;
            }
        }

        // 主循环
        std::cout << "\n[Main] Running (Press Ctrl+C to stop)..." << std::endl;

        int loop_count = 0;
        while (g_running && loop_count < 30) {  // 最多运行30秒或直到收到信号
            std::this_thread::sleep_for(std::chrono::seconds(1));

            // 每5秒打印一次指标
            if (++loop_count % 5 == 0) {
                print_metrics(manager);
            }
        }

        // 测试导出切片
        if (!stream_ids.empty()) {
            std::cout << "\n[Main] Testing clip export..." << std::endl;
            std::string clip_path = manager.export_clip(stream_ids[0], "test_event_001", 2, 3);
            if (!clip_path.empty()) {
                std::cout << "  Exported clip: " << clip_path << std::endl;
            }
        }

        // 停止所有流
        std::cout << "\n[Main] Stopping streams..." << std::endl;
        for (const auto& id : stream_ids) {
            manager.stop_stream(id);
            std::cout << "  Stopped: " << id << std::endl;
        }

        // 最终指标
        std::cout << "\n[Main] Final metrics:" << std::endl;
        print_metrics(manager);

        std::cout << "\n[Main] Test completed successfully!" << std::endl;
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "[Main] Error: " << e.what() << std::endl;
        return 1;
    }
}
