// cpp-core routes. order the worker uses them in:
//   /features -> (ml /predict for the genre) -> /compose w/ features + genre
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

// S3 policy already caps uploads at 10MB, 12 is just a bit of slack
constexpr size_t MAX_REQUEST_BYTES = 12 * 1024 * 1024;

// body = raw image bytes (not multipart, the worker just sends the S3 object as is)
void handleFeatures(const httplib::Request& req, httplib::Response& res) {
  ImageFeatures features = extractFeatures(req.body);
  res.set_content(json{{"features", features.toArray()}}.dump(), "application/json");
}

// features + genre -> plan -> midi bytes
void handleCompose(const httplib::Request& req, httplib::Response& res) {
  json body = json::parse(req.body);
  auto features = ImageFeatures::fromArray(body.at("features").get<std::array<float, 8>>());
  Genre genre = parseGenre(body.at("genre").get<std::string>());

  SongPlan plan = planSong(features, genre);
  res.set_content(composeMidi(plan), "audio/midi");
}

// IMPORTANT: status code = what the worker does next
//   400 -> bad input (broken image, bad json, unknown genre). retrying won't help -> fail the job
//   500 -> something else broke, maybe temporary -> worker retries
// so anything thrown for bad input HAS to be invalid_argument or a json error
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
