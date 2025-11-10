cmake_minimum_required(VERSION 3.15)
project(soundcanvas_core)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include headers
include_directories(${CMAKE_SOURCE_DIR}/include)
include_directories(${CMAKE_SOURCE_DIR}/vendor)

# Source files
set(SOURCES
    src/main.cpp
    src/ImageFeatures.cpp
    src/AudioEngine.cpp
    src/MusicMapping.cpp
)

add_executable(soundcanvas_core ${SOURCES})

# Later: add libraries if needed
