# cpp-core: builds the C++ server, then copies just the binary into a small image.
FROM gcc:13 AS build
RUN apt-get update && apt-get install -y cmake && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY CMakeLists.txt .
COPY include include
COPY src src
COPY vendor vendor
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j

FROM debian:bookworm-slim
COPY --from=build /usr/local/lib64/libstdc++.so.6 /usr/lib/x86_64-linux-gnu/libstdc++.so.6
COPY --from=build /src/build/soundcanvas_core /usr/local/bin/soundcanvas_core
EXPOSE 8080
CMD ["soundcanvas_core"]
