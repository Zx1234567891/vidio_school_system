#pragma once

#include <thread>
#include <vector>
#include <queue>
#include <functional>
#include <future>
#include <mutex>
#include <condition_variable>
#include <atomic>

namespace campus_guard {

/**
 * 固定大小线程池
 *
 * 核心约束：
 * - 线程数固定，不动态扩容
 * - 任务队列有界，满时拒绝或丢弃
 * - 支持优雅关闭
 */
class ThreadPool {
public:
    explicit ThreadPool(size_t num_threads);
    ~ThreadPool();

    // 禁止拷贝
    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;

    // 提交任务
    template<typename F, typename... Args>
    auto submit(F&& f, Args&&... args) -> std::future<std::invoke_result_t<F, Args...>> {
        using return_type = std::invoke_result_t<F, Args...>;

        auto task = std::make_shared<std::packaged_task<return_type()>>(
            std::bind(std::forward<F>(f), std::forward<Args>(args)...)
        );

        std::future<return_type> result = task->get_future();

        {
            std::unique_lock<std::mutex> lock(queue_mutex_);

            if (stop_) {
                throw std::runtime_error("Cannot submit task to stopped thread pool");
            }

            tasks_.emplace([task]() { (*task)(); });
        }

        condition_.notify_one();
        return result;
    }

    // 获取统计信息
    size_t get_thread_count() const { return workers_.size(); }
    size_t get_pending_count() const;

    // 优雅关闭
    void shutdown();

private:
    void worker_loop();

    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> tasks_;

    mutable std::mutex queue_mutex_;
    std::condition_variable condition_;
    std::atomic<bool> stop_{false};
};

} // namespace campus_guard
