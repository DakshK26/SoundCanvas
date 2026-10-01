// cpp-core's entry point: serve HTTP on $PORT, or 8080 if it isn't set.
// All the work is in HttpServer.cpp. The Dockerfile runs this binary and exposes 8080.
#include <cstdlib>
#include <string>

#include "HttpServer.hpp"

int main() {
  // getenv returns null when PORT is unset. If listening fails, runHttpServer throws and the
  // uncaught exception ends the process with an error instead of leaving it running idle.
  const char* port = std::getenv("PORT");
  runHttpServer(port ? std::stoi(port) : 8080);
  return 0;
}
