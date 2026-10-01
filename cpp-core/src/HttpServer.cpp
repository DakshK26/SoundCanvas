// cpp-core's HTTP API. The worker calls /features with the image, then /compose with the features
// and the genre. Nothing is stored between calls; bytes or JSON in, a result out.
// The callers are extractFeatures and composeMidi in api/src/serviceClients.ts, run from
// api/src/pipeline.ts. This file calls ImageFeatures.cpp, SongPlanner.cpp and Composer.cpp.
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

// POST /features
// The body is the raw image bytes, not multipart.
// Replies {"features": [8 numbers]} in the order of ImageFeatures::toArray. The worker passes
// the same array on to ml's /predict and then back here to /compose.
void handleFeatures(const httplib::Request& req, httplib::Response& res) {
  ImageFeatures features = extractFeatures(req.body);
  res.set_content(json{{"features", features.toArray()}}.dump(), "application/json");
}

// POST /compose
// {"features": [8 numbers], "genre": "HOUSE"} in, a .mid file out.
void handleCompose(const httplib::Request& req, httplib::Response& res) {
  // Each step throws on bad input: parse on broken JSON, at() on a missing key, get() on the
  // wrong type or fewer than 8 numbers (extra numbers are ignored), fromArray on an
  // out-of-range value, parseGenre on an unknown genre.
  json body = json::parse(req.body);
  auto features = ImageFeatures::fromArray(body.at("features").get<std::array<float, 8>>());
  Genre genre = parseGenre(body.at("genre").get<std::string>());

  // Plan first (tempo, key, sections), then write the notes. The body is binary MIDI bytes.
  SongPlan plan = planSong(features, genre);
  res.set_content(composeMidi(plan), "audio/midi");
}

// Error mapping for every route.
// The worker retries a 500 but not a 400, so bad input has to throw invalid_argument or a
// json error. In api/src/serviceClients.ts a 4xx becomes a PermanentError and the job fails at
// once, because the same input would fail again. Anything else is treated as a bug or a
// temporary problem, logged here, and sent as a 500 so the job goes back on the queue.
void handleError(const httplib::Request&, httplib::Response& res, std::exception_ptr error) {
  // Rethrowing the stored exception lets the catch blocks below sort it by type.
  try {
    std::rethrow_exception(error);
  } catch (const std::invalid_argument& e) {
    // A bad image, an out-of-range feature or an unknown genre.
    res.status = 400;
    res.set_content(e.what(), "text/plain");
  } catch (const json::exception& e) {
    // Broken JSON, a missing key or a value of the wrong type.
    res.status = 400;
    res.set_content(e.what(), "text/plain");
  } catch (const std::exception& e) {
    // Only unexpected errors are logged; a 400 is the caller's mistake.
    std::cerr << "[cpp-core] " << e.what() << std::endl;
    res.status = 500;
    res.set_content(e.what(), "text/plain");
  }
}

}  // namespace

// cpp-httplib runs each request on a thread from its pool; the handlers share no state.
void runHttpServer(int port) {
  httplib::Server server;
  // Larger bodies get a 413 from httplib before a handler runs.
  server.set_payload_max_length(MAX_REQUEST_BYTES);
  server.Post("/features", handleFeatures);
  server.Post("/compose", handleCompose);
  // GET /health: the container health check curls this, so it does no real work.
  server.Get("/health", [](const httplib::Request&, httplib::Response& res) {
    res.set_content(R"({"ok":true})", "application/json");
  });
  // Any exception a handler throws ends up in handleError instead of killing the server.
  server.set_exception_handler(handleError);

  // 0.0.0.0 so other containers can reach it, not only localhost. listen blocks until the
  // server stops and returns false if the port can't be bound.
  std::cout << "[cpp-core] listening on port " << port << std::endl;
  if (!server.listen("0.0.0.0", port)) {
    throw std::runtime_error("Could not listen on port " + std::to_string(port));
  }
}
