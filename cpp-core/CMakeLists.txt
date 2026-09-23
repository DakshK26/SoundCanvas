cmake_minimum_required(VERSION 3.15)
project(soundcanvas_core CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(soundcanvas_core
    src/main.cpp
    src/HttpServer.cpp
    src/ImageFeatures.cpp
    src/GenreTemplate.cpp
    src/SectionPlanner.cpp
    src/Composer.cpp
    src/MidiWriter.cpp
)

# include/ holds our headers; vendor/ holds single-file libraries:
# cpp-httplib (HTTP server), nlohmann/json (JSON), stb_image (JPG/PNG decoding).
target_include_directories(soundcanvas_core PRIVATE include vendor)

find_package(Threads REQUIRED)
target_link_libraries(soundcanvas_core PRIVATE Threads::Threads)
