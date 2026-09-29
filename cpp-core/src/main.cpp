#include <cstdlib>
#include <string>

#include "HttpServer.hpp"

int main() {
  const char* port = std::getenv("PORT");
  runHttpServer(port ? std::stoi(port) : 8080);
  return 0;
}
