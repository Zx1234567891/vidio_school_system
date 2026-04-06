cmake_minimum_required(VERSION 3.20)
project(CampusGuardStreamCore VERSION 0.1.0 LANGUAGES CXX)

# C++20 标准
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 编译选项
if(MSVC)
    add_compile_options(/W4 /WX-)
    add_compile_definitions(NOMINMAX _CRT_SECURE_NO_WARNINGS)
else()
    add_compile_options(-Wall -Wextra -Wpedantic -Wno-unused-parameter -fPIC)
endif()

# 查找 FFmpeg (支持 pkg-config 或直接指定路径)
if(WIN32)
    # Windows: 直接指定 FFmpeg 路径
    set(FFMPEG_ROOT "${FFMPEG_ROOT}" CACHE PATH "FFmpeg root directory")
    if(NOT FFMPEG_ROOT)
        set(FFMPEG_ROOT "C:/ffmpeg" CACHE PATH "FFmpeg root directory" FORCE)
    endif()

    set(FFMPEG_INCLUDE_DIRS "${FFMPEG_ROOT}/include")
    set(FFMPEG_LIBRARIES
        "${FFMPEG_ROOT}/lib/avcodec.lib"
        "${FFMPEG_ROOT}/lib/avformat.lib"
        "${FFMPEG_ROOT}/lib/avutil.lib"
        "${FFMPEG_ROOT}/lib/swscale.lib"
        "${FFMPEG_ROOT}/lib/swresample.lib"
    )
    set(FFMPEG_CFLAGS_OTHER "")
    message(STATUS "FFmpeg root: ${FFMPEG_ROOT}")
    message(STATUS "FFmpeg includes: ${FFMPEG_INCLUDE_DIRS}")
    message(STATUS "FFmpeg libraries: ${FFMPEG_LIBRARIES}")
else()
    # Linux/Mac: 使用 pkg-config
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(FFMPEG REQUIRED
        libavcodec
        libavformat
        libavutil
        libswscale
        libswresample
    )
endif()

# 查找线程库
find_package(Threads REQUIRED)

# 源文件
set(SOURCES
    src/types.cpp
    src/thread_pool.cpp
    src/bounded_queue.cpp
    src/metrics_collector.cpp
    src/reconnect_controller.cpp
    src/clip_exporter.cpp
    src/ffmpeg_decoder.cpp
    src/stream_session.cpp
    src/stream_manager.cpp
    src/c_api.cpp
)

# 头文件
set(HEADERS
    include/stream_core/types.hpp
    include/stream_core/thread_pool.hpp
    include/stream_core/bounded_queue.hpp
    include/stream_core/metrics_collector.hpp
    include/stream_core/ring_buffer.hpp
    include/stream_core/reconnect_controller.hpp
    include/stream_core/clip_exporter.hpp
    include/stream_core/ffmpeg_decoder.hpp
    include/stream_core/stream_session.hpp
    include/stream_core/stream_manager.hpp
    include/stream_core/c_api.hpp
)

# 创建静态库
add_library(stream_core STATIC ${SOURCES})

target_include_directories(stream_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
        ${FFMPEG_INCLUDE_DIRS}
)

target_link_libraries(stream_core
    PUBLIC
        ${FFMPEG_LIBRARIES}
        Threads::Threads
)

target_compile_options(stream_core
    PUBLIC
        ${FFMPEG_CFLAGS_OTHER}
)

# 创建共享库 (供 Python 调用)
add_library(stream_core_shared SHARED ${SOURCES})
set_target_properties(stream_core_shared PROPERTIES
    OUTPUT_NAME "campus_guard_stream"
    PREFIX ""
    WINDOWS_EXPORT_ALL_SYMBOLS ON
)

target_include_directories(stream_core_shared
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        ${FFMPEG_INCLUDE_DIRS}
)

target_link_libraries(stream_core_shared
    PUBLIC
        ${FFMPEG_LIBRARIES}
        Threads::Threads
)

# 可执行文件
add_executable(stream_core_app src/main.cpp)
target_link_libraries(stream_core_app PRIVATE stream_core)

# 测试
enable_testing()
add_subdirectory(tests)

# 安装
install(TARGETS stream_core stream_core_shared stream_core_app
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/ DESTINATION include)
