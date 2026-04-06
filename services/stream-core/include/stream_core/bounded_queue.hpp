#pragma once

#include <queue>
#include <mutex>
#include <condition_variable>
#include <optional>
#include <atomic>

namespace campus_guard {

/**
 * 有界队列
 *
 * 核心约束：
 * - 容量固定，满时 push 返回 false 或阻塞（配置决定）
 * - 支持超时 pop
 * - 线程安全
 */
template<typename T>
class BoundedQueue {
public:
    explicit BoundedQueue(size_t capacity)
        : capacity_(capacity), dropped_count_(0) {}

    // 非阻塞 push，满时返回 false
    bool try_push(T item) {
        std::unique_lock<std::mutex> lock(mutex_);

        if (queue_.size() >= capacity_) {
            ++dropped_count_;
            return false;  // 队列满，丢帧策略
        }

        queue_.push(std::move(item));
        not_empty_.notify_one();
        return true;
    }

    // 阻塞 pop
    std::optional<T> pop() {
        std::unique_lock<std::mutex> lock(mutex_);

        not_empty_.wait(lock, [this] { return !queue_.empty() || shutdown_; });

        if (queue_.empty()) {
            return std::nullopt;
        }

        T item = std::move(queue_.front());
        queue_.pop();
        return item;
    }

    // 超时 pop
    template<typename Rep, typename Period>
    std::optional<T> pop_for(const std::chrono::duration<Rep, Period>& timeout) {
        std::unique_lock<std::mutex> lock(mutex_);

        if (!not_empty_.wait_for(lock, timeout, [this] { return !queue_.empty() || shutdown_; })) {
            return std::nullopt;  // 超时
        }

        if (queue_.empty()) {
            return std::nullopt;
        }

        T item = std::move(queue_.front());
        queue_.pop();
        return item;
    }

    size_t size() const {
        std::unique_lock<std::mutex> lock(mutex_);
        return queue_.size();
    }

    size_t capacity() const { return capacity_; }

    uint64_t dropped_count() const { return dropped_count_.load(); }

    void shutdown() {
        std::unique_lock<std::mutex> lock(mutex_);
        shutdown_ = true;
        not_empty_.notify_all();
    }

private:
    std::queue<T> queue_;
    mutable std::mutex mutex_;
    std::condition_variable not_empty_;

    size_t capacity_;
    std::atomic<uint64_t> dropped_count_;
    bool shutdown_ = false;
};

} // namespace campus_guard
