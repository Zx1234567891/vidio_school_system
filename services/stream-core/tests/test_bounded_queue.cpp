#include "stream_core/bounded_queue.hpp"

#include <iostream>
#include <cassert>
#include <thread>
#include <vector>

using namespace campus_guard;

int test_bounded_queue() {
    std::cout << "[Test] Bounded Queue..." << std::endl;

    // 测试基本操作
    BoundedQueue<int> queue(5);

    assert(queue.capacity() == 5);
    assert(queue.size() == 0);
    std::cout << "  Initial state: OK" << std::endl;

    // 测试 push
    for (int i = 0; i < 5; ++i) {
        assert(queue.try_push(i));
    }
    assert(queue.size() == 5);
    std::cout << "  Push to capacity: OK" << std::endl;

    // 测试满队列拒绝
    assert(!queue.try_push(99));
    assert(queue.dropped_count() == 1);
    std::cout << "  Drop when full: OK" << std::endl;

    // 测试 pop
    auto val = queue.pop();
    assert(val.has_value() && val.value() == 0);
    assert(queue.size() == 4);
    std::cout << "  Pop: OK" << std::endl;

    // 测试 shutdown
    queue.shutdown();
    auto empty = queue.pop();
    assert(!empty.has_value());
    std::cout << "  Shutdown: OK" << std::endl;

    std::cout << "[Test] Bounded Queue: PASSED" << std::endl;
    return 0;
}

int main(int argc, char* argv[]) {
    if (argc > 1 && std::string(argv[1]) == "test_bounded_queue") {
        return test_bounded_queue();
    }
    return test_bounded_queue();
}
