cmake_minimum_required(VERSION 3.15)
project(soundcanvas_core)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(${CMAKE_SOURCE_DIR}/include)
include_directories(${CMAKE_SOURCE_DIR}/vendor)

set(SOURCES
    src/main.cpp
    src/ImageFeatures.cpp
    src/AudioEngine.cpp
    src/MusicMapping.cpp
    src/ModelClient.cpp
    src/HttpServer.cpp
    src/MusicalStyle.cpp
)

add_executable(soundcanvas_core ${SOURCES})
