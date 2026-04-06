#include "stream_core/reconnect_controller.hpp"

#include <algorithm>

namespace campus_guard {

ReconnectController::Config::Config()
    : max_attempts(5)
    , initial_interval_ms(1000)
    , max_interval_ms(30000)
    , backoff_multiplier(2.0) {}

ReconnectController::ReconnectController(Config config)
    : config_(config)
    , current_interval_ms_(config.initial_interval_ms) {}

void ReconnectController::reset() {
    attempt_count_ = 0;
    current_interval_ms_ = config_.initial_interval_ms;
}

bool ReconnectController::should_reconnect() const {
    return attempt_count_ < config_.max_attempts;
}

uint32_t ReconnectController::get_next_wait_time() {
    uint32_t wait_time = current_interval_ms_;

    // 指数退避
    current_interval_ms_ = static_cast<uint32_t>(
        current_interval_ms_ * config_.backoff_multiplier
    );
    current_interval_ms_ = std::min(current_interval_ms_, config_.max_interval_ms);

    return wait_time;
}

void ReconnectController::record_attempt() {
    ++attempt_count_;
    last_attempt_time_ = std::chrono::steady_clock::now();
}

bool ReconnectController::is_exhausted() const {
    return attempt_count_ >= config_.max_attempts;
}

} // namespace campus_guard
