#pragma once

#include <string>

// Runs an HTTP server on the given port and blocks the current thread.
// Throws std::runtime_error on fatal startup errors.
void runHttpServer(
    int port,
    const std::string& defaultMode,   // "heuristic" or "model"
    const std::string& outputDir      // where to write generated WAVs
);
