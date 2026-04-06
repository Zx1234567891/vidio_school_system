#include "stream_core/thread_pool.hpp"
#include "stream_core/bounded_queue.hpp"
#include "stream_core/stream_manager.hpp"
#include "stream_core/stream_session.hpp"
#include "stream_core/reconnect_controller.hpp"
#include "stream_core/types.hpp"

#include <iostream>
#include <cassert>
#include <chrono>
#include <thread>
#include <vector>

using namespace campus_guard;

// 测试线程池
int test_thread_pool() {
    std::cout << "\n========== Test: Thread Pool ==========" << std::endl;

    ThreadPool pool(4);

    // 测试基本提交
    auto future1 = pool.submit([]() -> int { return 42; });
    assert(future1.get() == 42);
    std::cout << "✓ Basic submit" << std::endl;

    // 测试多个任务
    std::vector<std::future<int>> futures;
    for (int i = 0; i < 10; ++i) {
        futures.push_back(pool.submit([i]() -> int {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            return i * i;
        }));
    }
    for (int i = 0; i < 10; ++i) {
        assert(futures[i].get() == i * i);
    }
    std::cout << "✓ Multiple tasks" << std::endl;

    // 测试线程数
    assert(pool.get_thread_count() == 4);
    std::cout << "✓ Thread count: " << pool.get_thread_count() << std::endl;

    // 测试待处理任务数
    assert(pool.get_pending_count() == 0);
    std::cout << "✓ Pending count: " << pool.get_pending_count() << std::endl;

    std::cout << "========== Thread Pool: PASSED ==========\n" << std::endl;
    return 0;
}

// 测试有界队列
int test_bounded_queue() {
    std::cout << "\n========== Test: Bounded Queue ==========" << std::endl;

    BoundedQueue<int> queue(5);

    assert(queue.capacity() == 5);
    assert(queue.size() == 0);
    std::cout << "✓ Initial state" << std::endl;

    // 测试 push
    for (int i = 0; i < 5; ++i) {
        assert(queue.try_push(i));
    }
    assert(queue.size() == 5);
    std::cout << "✓ Push to capacity" << std::endl;

    // 测试满队列拒绝（背压策略）
    assert(!queue.try_push(99));
    assert(queue.dropped_count() == 1);
    std::cout << "✓ Drop when full (backpressure)" << std::endl;

    // 测试 pop
    auto val = queue.pop();
    assert(val.has_value() && val.value() == 0);
    assert(queue.size() == 4);
    std::cout << "✓ Pop" << std::endl;

    // 测试超时 pop
    auto empty = queue.pop_for(std::chrono::milliseconds(10));
    assert(empty.has_value());  // 队列还有数据
    std::cout << "✓ Pop with timeout" << std::endl;

    // 测试 shutdown
    queue.shutdown();
    auto after_shutdown = queue.pop();
    assert(!after_shutdown.has_value());
    std::cout << "✓ Shutdown" << std::endl;

    std::cout << "========== Bounded Queue: PASSED ==========\n" << std::endl;
    return 0;
}

// 测试流生命周期
int test_stream_lifecycle() {
    std::cout << "\n========== Test: Stream Lifecycle ==========" << std::endl;

    StreamManager manager;

    // 测试创建流
    StreamConfig config;
    config.name = "Test Stream";
    config.input_type = InputType::FILE;
    config.url = "test_video.mp4";
    config.max_queue_size = 10;
    config.ring_buffer_seconds = 5;

    std::string id = manager.create_stream(config);
    assert(!id.empty());
    assert(manager.get_stream_count() == 1);
    std::cout << "✓ Create stream: " << id << std::endl;

    // 测试获取流
    auto session = manager.get_stream(id);
    assert(session != nullptr);
    assert(session->get_id() == id);
    std::cout << "✓ Get stream" << std::endl;

    // 测试状态
    assert(session->get_status() == StreamStatus::INIT);
    std::cout << "✓ Initial status: " << status_to_string(session->get_status()) << std::endl;

    // 测试指标（未启动时）
    auto metrics = session->get_metrics();
    assert(metrics.fps == 0.0);
    std::cout << "✓ Initial metrics" << std::endl;

    // 测试停止（未启动的流）
    manager.stop_stream(id);
    std::cout << "✓ Stop before start (no-op)" << std::endl;

    // 测试删除
    assert(manager.remove_stream(id));
    assert(manager.get_stream_count() == 0);
    std::cout << "✓ Remove stream" << std::endl;

    // 测试最大流数限制
    bool exception_thrown = false;
    try {
        for (size_t i = 0; i < StreamManager::MAX_STREAMS + 1; ++i) {
            StreamConfig cfg;
            cfg.name = "Stream " + std::to_string(i);
            cfg.input_type = InputType::FILE;
            cfg.url = "test.mp4";
            manager.create_stream(cfg);
        }
    } catch (const std::runtime_error& e) {
        exception_thrown = true;
        std::cout << "✓ Max streams limit enforced: " << e.what() << std::endl;
    }
    assert(exception_thrown);

    std::cout << "========== Stream Lifecycle: PASSED ==========\n" << std::endl;
    return 0;
}

// 测试重连控制器
int test_reconnect_controller() {
    std::cout << "\n========== Test: Reconnect Controller ==========" << std::endl;

    ReconnectController::Config config;
    config.max_attempts = 3;
    config.initial_interval_ms = 100;
    config.max_interval_ms = 1000;
    config.backoff_multiplier = 2.0;

    ReconnectController controller(config);

    // 测试初始状态
    assert(controller.should_reconnect());
    assert(controller.get_attempt_count() == 0);
    assert(!controller.is_exhausted());
    std::cout << "✓ Initial state" << std::endl;

    // 测试退避策略
    uint32_t wait1 = controller.get_next_wait_time();
    assert(wait1 == 100);
    controller.record_attempt();

    uint32_t wait2 = controller.get_next_wait_time();
    assert(wait2 == 200);  // 100 * 2
    controller.record_attempt();

    uint32_t wait3 = controller.get_next_wait_time();
    assert(wait3 == 400);  // 200 * 2
    controller.record_attempt();

    std::cout << "✓ Exponential backoff: 100ms -> 200ms -> 400ms" << std::endl;

    // 测试用尽
    assert(controller.is_exhausted());
    assert(!controller.should_reconnect());
    std::cout << "✓ Reconnect exhausted after 3 attempts" << std::endl;

    // 测试重置
    controller.reset();
    assert(controller.get_attempt_count() == 0);
    assert(controller.should_reconnect());
    std::cout << "✓ Reset" << std::endl;

    std::cout << "========== Reconnect Controller: PASSED ==========\n" << std::endl;
    return 0;
}

// 测试全局指标
int test_global_metrics() {
    std::cout << "\n========== Test: Global Metrics ==========" << std::endl;

    StreamManager manager(4);

    // 初始状态
    auto metrics = manager.get_global_metrics();
    assert(metrics.total_streams == 0);
    assert(metrics.active_streams == 0);
    assert(metrics.thread_pool_size == 4);
    assert(metrics.pending_tasks == 0);
    std::cout << "✓ Initial global metrics" << std::endl;

    // 创建多个流
    for (int i = 0; i < 5; ++i) {
        StreamConfig config;
        config.name = "Stream " + std::to_string(i);
        config.input_type = InputType::FILE;
        config.url = "test" + std::to_string(i) + ".mp4";
        manager.create_stream(config);
    }

    metrics = manager.get_global_metrics();
    assert(metrics.total_streams == 5);
    std::cout << "✓ Metrics after creating 5 streams" << std::endl;

    // 列出流ID
    auto ids = manager.list_stream_ids();
    assert(ids.size() == 5);
    std::cout << "✓ List stream IDs: " << ids.size() << " streams" << std::endl;

    std::cout << "========== Global Metrics: PASSED ==========\n" << std::endl;
    return 0;
}

// 主函数
int main(int argc, char* argv[]) {
    std::cout << "\n";
    std::cout << "╔══════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║   Campus Guard Stream Core - Unit Tests (P1)     ║" << std::endl;
    std::cout << "╚══════════════════════════════════════════════════╝" << std::endl;

    int result = 0;

    // 运行所有测试
    result |= test_thread_pool();
    result |= test_bounded_queue();
    result |= test_stream_lifecycle();
    result |= test_reconnect_controller();
    result |= test_global_metrics();

    if (result == 0) {
        std::cout << "\n✅ ALL TESTS PASSED!" << std::endl;
    } else {
        std::cout << "\n❌ SOME TESTS FAILED!" << std::endl;
    }

    return result;
}
