#include "stream_core/thread_pool.hpp"

#include <iostream>
#include <cassert>
#include <chrono>

using namespace campus_guard;

int test_thread_pool() {
    std::cout << "[Test] Thread Pool..." << std::endl;

    ThreadPool pool(4);

    // 测试基本提交
    auto future1 = pool.submit([]() -> int {
        return 42;
    });

    assert(future1.get() == 42);
    std::cout << "  Basic submit: OK" << std::endl;

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
    std::cout << "  Multiple tasks: OK" << std::endl;

    // 测试线程数
    assert(pool.get_thread_count() == 4);
    std::cout << "  Thread count: OK" << std::endl;

    std::cout << "[Test] Thread Pool: PASSED" << std::endl;
    return 0;
}

int main(int argc, char* argv[]) {
    if (argc > 1 && std::string(argv[1]) == "test_thread_pool") {
        return test_thread_pool();
    }

    // 运行所有测试
    return test_thread_pool();
}
