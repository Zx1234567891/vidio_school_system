#pragma once

#include <cstdint>
#include <chrono>
#include <functional>
#include <atomic>

namespace campus_guard {

/**
 * 重连控制器
 *
 * 管理连接断开后的自动重连逻辑
 */
class ReconnectController {
public:
    struct Config {
        Config();
        uint32_t max_attempts;           // 最大重连次数
        uint32_t initial_interval_ms;    // 初始重连间隔
        uint32_t max_interval_ms;        // 最大重连间隔
        double backoff_multiplier;       // 退避乘数
    };

    explicit ReconnectController(Config config = {});

    /**
     * 重置状态
     */
    void reset();

    /**
     * 是否应该尝试重连
     */
    bool should_reconnect() const;

    /**
     * 获取下一次重连等待时间（毫秒）
     */
    uint32_t get_next_wait_time();

    /**
     * 记录一次重连尝试
     */
    void record_attempt();

    /**
     * 获取当前尝试次数
     */
    uint32_t get_attempt_count() const { return attempt_count_.load(); }

    /**
     * 是否已用尽所有重连机会
     */
    bool is_exhausted() const;

    /**
     * 获取最后一次重连时间
     */
    std::chrono::steady_clock::time_point get_last_attempt_time() const {
        return last_attempt_time_;
    }

private:
    Config config_;
    std::atomic<uint32_t> attempt_count_{0};
    uint32_t current_interval_ms_;
    std::chrono::steady_clock::time_point last_attempt_time_;
};

} // namespace campus_guard
