#include "ModelClient.hpp"

#include "httplib.h"
#include "json.hpp"

#include <cstdlib>
#include <stdexcept>

using json = nlohmann::json;

ModelClient::ModelClient(const std::string& baseUrl)
    : baseUrl_(baseUrl) {}

// Helper to split baseUrl_ into host + path for httplib
static void parseUrl(const std::string& url, std::string& host, int& port, std::string& path) {
    // Expect something like: http://localhost:8501/v1/models/soundcanvas:predict
    const std::string prefix = "http://";
    if (url.rfind(prefix, 0) != 0) {
        throw std::runtime_error("Only http:// URLs are supported for TF Serving");
    }

    std::string withoutScheme = url.substr(prefix.size());
    auto slashPos = withoutScheme.find('/');
    std::string hostPort = slashPos == std::string::npos ? withoutScheme
                                                         : withoutScheme.substr(0, slashPos);
    path = slashPos == std::string::npos ? "/" : withoutScheme.substr(slashPos);

    // host[:port]
    auto colonPos = hostPort.find(':');
    if (colonPos == std::string::npos) {
        host = hostPort;
        port = 80;
    } else {
        host = hostPort.substr(0, colonPos);
        port = std::stoi(hostPort.substr(colonPos + 1));
    }
}

MusicParameters ModelClient::predict(const ImageFeatures& f) const {
    std::string host;
    int port;
    std::string path;
    parseUrl(baseUrl_, host, port, path);

    httplib::Client cli(host, port);
    cli.set_read_timeout(5, 0);  // 5 seconds

    // Build JSON payload: {"instances": [[avgR, avgG, avgB, brightness]]}
    json payload;
    payload["instances"] = json::array();
    payload["instances"].push_back(
        {f.avgR, f.avgG, f.avgB, f.brightness}
    );

    auto res = cli.Post(path.c_str(), payload.dump(), "application/json");
    if (!res) {
        throw std::runtime_error("Failed to reach TF Serving");
    }
    if (res->status != 200) {
        throw std::runtime_error("TF Serving returned non-200: " + std::to_string(res->status));
    }

    json body = json::parse(res->body);

    if (!body.contains("predictions") || !body["predictions"].is_array() || body["predictions"].empty()) {
        throw std::runtime_error("TF Serving response missing 'predictions'");
    }

    const auto& pred = body["predictions"][0];
    if (!pred.is_array() || pred.size() < 5) {
        throw std::runtime_error("TF Serving prediction has wrong shape");
    }

    // Order must match music_params_to_vector: [tempo, baseFreq, brightness, volume, duration]
    MusicParameters params;
    params.tempoBpm        = static_cast<float>(pred[0].get<double>());
    params.baseFrequency   = static_cast<float>(pred[1].get<double>());
    params.brightness      = static_cast<float>(pred[2].get<double>());
    params.volume          = static_cast<float>(pred[3].get<double>());
    params.durationSeconds = static_cast<float>(pred[4].get<double>());

    return params;
}
