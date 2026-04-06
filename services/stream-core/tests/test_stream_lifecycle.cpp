#include "stream_core/stream_manager.hpp"
#include "stream_core/stream_session.hpp"

#include <iostream>
#include <cassert>
#include <chrono>
#include <thread>

using namespace campus_guard;

int test_stream_lifecycle() {
    std::cout << "[Test] Stream Lifecycle..." << std::endl;

    StreamManager manager;

    // 测试创建流
    StreamConfig config;
    config.name = "Test Stream";
    config.input_type = InputType::FILE;
    config.url = "/tmp/test.mp4";

    std::string id = manager.create_stream(config);
    assert(!id.empty());
    assert(manager.get_stream_count() == 1);
    std::cout << "  Create stream: OK" << std::endl;

    // 测试获取流
    auto session = manager.get_stream(id);
    assert(session != nullptr);
    assert(session->get_id() == id);
    std::cout << "  Get stream: OK" << std::endl;

    // 测试启动
    assert(manager.start_stream(id));
    assert(session->get_status() == StreamStatus::RUNNING);
    std::cout << "  Start stream: OK" << std::endl;

    // 运行一小段时间
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    // 测试指标
    auto metrics = session->get_metrics();
    assert(metrics.fps >= 0);
    std::cout << "  Metrics: OK" << std::endl;

    // 测试停止
    assert(manager.stop_stream(id));
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    assert(session->get_status() == StreamStatus::STOPPED);
    std::cout << "  Stop stream: OK" << std::endl;

    // 测试删除
    assert(manager.remove_stream(id));
    assert(manager.get_stream_count() == 0);
    std::cout << "  Remove stream: OK" << std::endl;

    // 测试最大流数限制
    bool exception_thrown = false;
    try {
        for (size_t i = 0; i < StreamManager::MAX_STREAMS + 1; ++i) {
            StreamConfig cfg;
            cfg.name = "Stream " + std::to_string(i);
            cfg.input_type = InputType::FILE;
            cfg.url = "/tmp/test.mp4";
            manager.create_stream(cfg);
        }
    } catch (const std::runtime_error& e) {
        exception_thrown = true;
    }
    assert(exception_thrown);
    std::cout << "  Max streams limit: OK" << std::endl;

    std::cout << "[Test] Stream Lifecycle: PASSED" << std::endl;
    return 0;
}

int main(int argc, char* argv[]) {
    if (argc > 1 && std::string(argv[1]) == "test_stream_lifecycle") {
        return test_stream_lifecycle();
    }
    return test_stream_lifecycle();
}
