cmake_minimum_required(VERSION 3.15)
project(soundcanvas_core)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(soundcanvas_core
    src/main.cpp
)

# Later: link libraries for HTTP, image processing, audio, etc.
