FROM gcc:13 AS builder

# Install CMake and dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy source files
COPY CMakeLists.txt ./
COPY include ./include
COPY src ./src
COPY vendor ./vendor

# Build the project
RUN mkdir -p build && cd build && \
    cmake .. && \
    make -j4

# Runtime stage
FROM debian:bookworm

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the newer libstdc++ from GCC 13 builder
COPY --from=builder /usr/local/lib64/libstdc++.so.6 /usr/lib/aarch64-linux-gnu/

# Copy binary from builder
COPY --from=builder /build/build/soundcanvas_core .

# Copy examples directory for default paths
COPY examples ./examples

# Expose HTTP port
EXPOSE 8080

# Default command (can be overridden in docker-compose)
CMD ["./soundcanvas_core", "--serve"]