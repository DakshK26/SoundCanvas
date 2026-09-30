// cpp-core's HTTP API. The worker calls /features with the image, then /compose with the features
// and the genre. Nothing is stored between calls; bytes or JSON in, a result out.
#include "HttpServer.hpp"

#include <array>
#include <iostream>
#include <stdexcept>

#include "Composer.hpp"
#include "ImageFeatures.hpp"
#include "SongPlanner.hpp"
#include "httplib.h"
#include "json.hpp"

using json = nlohmann::json;

namespace {

// The S3 upload policy already caps images at 10 MB.
constexpr size_t MAX_REQUEST_BYTES = 12 * 1024 * 1024;

// The body is the raw image bytes, not multipart.
void handleFeatures(const httplib::Request& req, httplib::Response& res) {
  ImageFeatures features = extractFeatures(req.body);
  res.set_content(json{{"features", features.toArray()}}.dump(), "application/json");
}

// {"features": [8 numbers], "genre": "HOUSE"} in, a .mid file out.
void handleCompose(const httplib::Request& req, httplib::Response& res) {
  json body = json::parse(req.body);
  auto features = ImageFeatures::fromArray(body.at("features").get<std::array<float, 8>>());
  Genre genre = parseGenre(body.at("genre").get<std::string>());

  SongPlan plan = planSong(features, genre);
  res.set_content(composeMidi(plan), "audio/midi");
}

// The worker retries a 500 but not a 400, so bad input has to throw invalid_argument or a
// json error.
void handleError(const httplib::Request&, httplib::Response& res, std::exception_ptr error) {
  try {
    std::rethrow_exception(error);
  } catch (const std::invalid_argument& e) {
    res.status = 400;
    res.set_content(e.what(), "text/plain");
  } catch (const json::exception& e) {
    res.status = 400;
    res.set_content(e.what(), "text/plain");
  } catch (const std::exception& e) {
    std::cerr << "[cpp-core] " << e.what() << std::endl;
    res.status = 500;
    res.set_content(e.what(), "text/plain");
  }
}

}  // namespace

// cpp-httplib runs each request on a thread from its pool; the handlers share no state.
void runHttpServer(int port) {
  httplib::Server server;
  server.set_payload_max_length(MAX_REQUEST_BYTES);
  server.Post("/features", handleFeatures);
  server.Post("/compose", handleCompose);
  server.Get("/health", [](const httplib::Request&, httplib::Response& res) {
    res.set_content(R"({"ok":true})", "application/json");
  });
  server.set_exception_handler(handleError);

  std::cout << "[cpp-core] listening on port " << port << std::endl;
  if (!server.listen("0.0.0.0", port)) {
    throw std::runtime_error("Could not listen on port " + std::to_string(port));
  }
}
