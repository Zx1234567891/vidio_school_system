#include "stream_core/thread_pool.hpp"

#include <iostream>

namespace campus_guard {

ThreadPool::ThreadPool(size_t num_threads) {
    workers_.reserve(num_threads);
    for (size_t i = 0; i < num_threads; ++i) {
        workers_.emplace_back(&ThreadPool::worker_loop, this);
    }
}

ThreadPool::~ThreadPool() {
    shutdown();
}

void ThreadPool::worker_loop() {
    while (true) {
        std::function<void()> task;

        {
            std::unique_lock<std::mutex> lock(queue_mutex_);

            condition_.wait(lock, [this] {
                return stop_ || !tasks_.empty();
            });

            if (stop_ && tasks_.empty()) {
                return;
            }

            task = std::move(tasks_.front());
            tasks_.pop();
        }

        task();
    }
}

size_t ThreadPool::get_pending_count() const {
    std::unique_lock<std::mutex> lock(queue_mutex_);
    return tasks_.size();
}

void ThreadPool::shutdown() {
    {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        stop_ = true;
    }

    condition_.notify_all();

    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
}

} // namespace campus_guard
