# Builds the music and image code as a static library, the HTTP server on top of it, and the
# tests when SOUNDCANVAS_TESTS is on. Tests link the library without starting a server.
cmake_minimum_required(VERSION 3.15)
project(soundcanvas_core CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra)
endif()

add_library(soundcanvas_lib STATIC
    src/ImageFeatures.cpp
    src/GenreTemplate.cpp
    src/SongPlanner.cpp
    src/Composer.cpp
    src/MidiWriter.cpp
)
target_include_directories(soundcanvas_lib PUBLIC include)
# SYSTEM keeps -Wall -Wextra quiet for the vendored headers.
target_include_directories(soundcanvas_lib SYSTEM PUBLIC vendor)

add_executable(soundcanvas_core src/main.cpp src/HttpServer.cpp)
find_package(Threads REQUIRED)
target_link_libraries(soundcanvas_core PRIVATE soundcanvas_lib Threads::Threads)

# Off by default because the Dockerfile doesn't copy tests/.
option(SOUNDCANVAS_TESTS "Build the unit tests" OFF)
if(SOUNDCANVAS_TESTS)
    enable_testing()
    add_executable(core_tests tests/test_core.cpp)
    target_link_libraries(core_tests PRIVATE soundcanvas_lib)
    # The parity test reads tests/feature_parity and the example photos.
    target_compile_definitions(core_tests PRIVATE REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")
    add_test(NAME core_tests COMMAND core_tests)
endif()
