# cpp-core, multi-stage: build w/ gcc, then only the binary goes into a slim image (way smaller)
FROM gcc:13 AS build
RUN apt-get update && apt-get install -y cmake && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY CMakeLists.txt .
COPY include include
COPY src src
COPY vendor vendor
# gotcha: gcc:13's libstdc++ is newer than bookworm's -> "GLIBCXX not found" at runtime.
# static link the C++ runtime so the binary doesn't care
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_EXE_LINKER_FLAGS="-static-libstdc++ -static-libgcc" \
    && cmake --build build -j

FROM debian:bookworm-slim
# curl only for the ECS health check
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/build/soundcanvas_core /usr/local/bin/soundcanvas_core
USER nobody
EXPOSE 8080
CMD ["soundcanvas_core"]
