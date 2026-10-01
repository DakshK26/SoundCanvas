# Two stages: build with gcc and cmake, then copy only the binary into a slim Debian image.
# The result serves HttpServer.cpp's API on 8080 for the worker in api/src/pipeline.ts.

# Build stage: the gcc image plus cmake.
FROM gcc:13 AS build
RUN apt-get update && apt-get install -y cmake && rm -rf /var/lib/apt/lists/*
# Only the files CMakeLists.txt needs for the server; tests/ is left out.
WORKDIR /src
COPY CMakeLists.txt .
COPY include include
COPY src src
COPY vendor vendor
# gcc:13's libstdc++ is newer than bookworm's, so without static linking the binary fails
# with "GLIBCXX not found".
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_EXE_LINKER_FLAGS="-static-libstdc++ -static-libgcc" \
    && cmake --build build -j

# Run stage: a small image with just the binary.
FROM debian:bookworm-slim
# curl is for the ECS health check.
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/build/soundcanvas_core /usr/local/bin/soundcanvas_core
# Runs without root, since the server never needs it.
USER nobody
# main.cpp listens on $PORT or 8080.
EXPOSE 8080
CMD ["soundcanvas_core"]
