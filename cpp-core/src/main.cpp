// cpp-core entry point: starts the HTTP server on $PORT (default 8080).
#include <cstdlib>
#include <string>

#include "HttpServer.hpp"

int main() {
  const char* port = std::getenv("PORT");
  runHttpServer(port ? std::stoi(port) : 8080);
  return 0;
}
