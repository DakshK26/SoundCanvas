# cpp-core: builds the C++ server, then copies just the binary into a small image.
FROM gcc:13 AS build
RUN apt-get update && apt-get install -y cmake && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY CMakeLists.txt .
COPY include include
COPY src src
COPY vendor vendor
# gcc:13 ships a newer C++ runtime than Debian's, so link it into the binary.
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_EXE_LINKER_FLAGS="-static-libstdc++ -static-libgcc" \
    && cmake --build build -j

FROM debian:bookworm-slim
# curl is only for the container health check.
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/build/soundcanvas_core /usr/local/bin/soundcanvas_core
USER nobody
EXPOSE 8080
CMD ["soundcanvas_core"]
