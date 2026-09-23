cmake_minimum_required(VERSION 3.15)
project(soundcanvas_core CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The music and image code, kept apart from the HTTP server so the tests can use it directly.
add_library(soundcanvas_lib STATIC
    src/ImageFeatures.cpp
    src/GenreTemplate.cpp
    src/SectionPlanner.cpp
    src/Composer.cpp
    src/MidiWriter.cpp
)
# include/ holds our headers; vendor/ holds single-file libraries:
# cpp-httplib (HTTP server), nlohmann/json (JSON), stb_image (JPG/PNG decoding).
target_include_directories(soundcanvas_lib PUBLIC include vendor)

add_executable(soundcanvas_core src/main.cpp src/HttpServer.cpp)
find_package(Threads REQUIRED)
target_link_libraries(soundcanvas_core PRIVATE soundcanvas_lib Threads::Threads)

# Off by default so the Docker build (which does not copy tests/) is unchanged.
#   cmake -B build -DSOUNDCANVAS_TESTS=ON && cmake --build build && ctest --test-dir build
option(SOUNDCANVAS_TESTS "Build the unit tests" OFF)
if(SOUNDCANVAS_TESTS)
    enable_testing()
    add_executable(core_tests tests/test_core.cpp)
    target_link_libraries(core_tests PRIVATE soundcanvas_lib)
    # The parity test reads tests/feature_parity/ and the example photos from the repo.
    target_compile_definitions(core_tests PRIVATE REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")
    add_test(NAME core_tests COMMAND core_tests)
endif()
