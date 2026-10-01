// Starts cpp-core's HTTP API (/features, /compose, /health) and blocks until it stops.
// Called from main.cpp; the routes live in HttpServer.cpp and are called by the worker through
// api/src/serviceClients.ts.
#pragma once

// Listens on all interfaces. Throws std::runtime_error if the port can't be bound.
void runHttpServer(int port);
