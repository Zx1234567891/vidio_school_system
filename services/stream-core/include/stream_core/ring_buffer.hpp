#pragma once

#include <vector>
#include <cstdint>
#include <optional>
#include <mutex>

namespace campus_guard {

/**
 * 环形缓冲区
 *
 * 用于存储最近 N 帧，支持异常切片导出
 */
template<typename T>
class RingBuffer {
public:
    explicit RingBuffer(size_t capacity)
        : capacity_(capacity), buffer_(capacity), head_(0), tail_(0), size_(0) {}

    // 写入数据
    void push(const T& item) {
        std::unique_lock<std::mutex> lock(mutex_);

        buffer_[head_] = item;
        head_ = (head_ + 1) % capacity_;

        if (size_ < capacity_) {
            ++size_;
        } else {
            tail_ = (tail_ + 1) % capacity_;
        }
    }

    // 获取最近 n 个元素
    std::vector<T> get_recent(size_t n) const {
        std::unique_lock<std::mutex> lock(mutex_);

        n = std::min(n, size_);
        std::vector<T> result;
        result.reserve(n);

        size_t idx = (head_ + capacity_ - n) % capacity_;
        for (size_t i = 0; i < n; ++i) {
            result.push_back(buffer_[idx]);
            idx = (idx + 1) % capacity_;
        }

        return result;
    }

    // 清空
    void clear() {
        std::unique_lock<std::mutex> lock(mutex_);
        head_ = tail_ = size_ = 0;
    }

    size_t size() const {
        std::unique_lock<std::mutex> lock(mutex_);
        return size_;
    }

    size_t capacity() const { return capacity_; }

    bool empty() const {
        std::unique_lock<std::mutex> lock(mutex_);
        return size_ == 0;
    }

private:
    size_t capacity_;
    std::vector<T> buffer_;
    size_t head_;
    size_t tail_;
    size_t size_;
    mutable std::mutex mutex_;
};

} // namespace campus_guard
