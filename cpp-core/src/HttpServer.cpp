// Routes for cpp-core. The gateway worker calls /features first, sends those
// numbers to the ml service for a genre, then calls /compose with both.
#include "HttpServer.hpp"

#include <array>
#include <iostream>
#include <stdexcept>

#include "Composer.hpp"
#include "ImageFeatures.hpp"
#include "SectionPlanner.hpp"
#include "httplib.h"
#include "json.hpp"

using json = nlohmann::json;

namespace {

// Uploads are capped at 10 MB by the S3 upload policy; the extra room is headroom, not a feature.
constexpr size_t MAX_REQUEST_BYTES = 12 * 1024 * 1024;

// Measures the uploaded image and returns its 8 features.
void handleFeatures(const httplib::Request& req, httplib::Response& res) {
  ImageFeatures features = extractFeatures(req.body);
  res.set_content(json{{"features", features.toArray()}}.dump(), "application/json");
}

// Plans and composes a song for the given features and genre.
void handleCompose(const httplib::Request& req, httplib::Response& res) {
  json body = json::parse(req.body);
  auto features = ImageFeatures::fromArray(body.at("features").get<std::array<float, 8>>());
  Genre genre = parseGenre(body.at("genre").get<std::string>());

  SongPlan plan = planSong(features, genre);
  res.set_content(composeMidi(plan), "audio/midi");
}

// Bad input (an undecodable image, malformed JSON, an unknown genre) is a 400:
// the worker gives up on the job, since retrying cannot fix it.
// Anything else is a 500, which the worker treats as temporary and retries.
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
