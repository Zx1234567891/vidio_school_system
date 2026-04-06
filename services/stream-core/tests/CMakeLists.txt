cmake_minimum_required(VERSION 3.20)

# 统一测试可执行文件
add_executable(stream_core_tests
    stream_core_tests.cpp
)

target_link_libraries(stream_core_tests PRIVATE stream_core)

# 添加测试
add_test(NAME StreamCoreTests COMMAND stream_core_tests)
