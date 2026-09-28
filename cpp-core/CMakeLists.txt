cmake_minimum_required(VERSION 3.15)
project(soundcanvas_core CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra)
endif()

# all the actual music/image logic as a lib, separate from the http server
# -> tests can link it without starting a server
add_library(soundcanvas_lib STATIC
    src/ImageFeatures.cpp
    src/GenreTemplate.cpp
    src/SectionPlanner.cpp
    src/Composer.cpp
    src/MidiWriter.cpp
)
# vendor/ = single header libs: cpp-httplib (server), nlohmann/json, stb_image (jpg/png decode)
target_include_directories(soundcanvas_lib PUBLIC include)
# SYSTEM so -Wall -Wextra doesn't spam warnings from the vendored headers, only mine
target_include_directories(soundcanvas_lib SYSTEM PUBLIC vendor)

add_executable(soundcanvas_core src/main.cpp src/HttpServer.cpp)
find_package(Threads REQUIRED)
target_link_libraries(soundcanvas_core PRIVATE soundcanvas_lib Threads::Threads)

# tests are OFF by default bc the Dockerfile doesn't copy tests/ in
#   cmake -B build -DSOUNDCANVAS_TESTS=ON && cmake --build build && ctest --test-dir build
option(SOUNDCANVAS_TESTS "Build the unit tests" OFF)
if(SOUNDCANVAS_TESTS)
    enable_testing()
    add_executable(core_tests tests/test_core.cpp)
    target_link_libraries(core_tests PRIVATE soundcanvas_lib)
    # parity test needs tests/feature_parity/ + the example photos, so point it at the repo root
    target_compile_definitions(core_tests PRIVATE REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")
    add_test(NAME core_tests COMMAND core_tests)
endif()
