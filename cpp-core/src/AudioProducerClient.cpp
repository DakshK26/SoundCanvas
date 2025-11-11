#include "AudioProducerClient.hpp"

#include <iostream>
#include <sstream>

#include "httplib.h"
#include "json.hpp"

using json = nlohmann::json;

AudioProducerClient::AudioProducerClient(const std::string& baseUrl)
    : baseUrl_(baseUrl), port_(9001) {
  parseUrl();
}

void AudioProducerClient::parseUrl() {
  // Parse URL format: http://host:port
  size_t protoEnd = baseUrl_.find("://");
  if (protoEnd == std::string::npos) {
    host_ = baseUrl_;
    return;
  }

  std::string rest = baseUrl_.substr(protoEnd + 3);
  size_t portPos = rest.find(':');

  if (portPos != std::string::npos) {
    host_ = rest.substr(0, portPos);
    port_ = std::stoi(rest.substr(portPos + 1));
  } else {
    host_ = rest;
    port_ = 9001;
  }
}

bool AudioProducerClient::produceTrack(
    const std::map<std::string, std::string>& stems,
    const std::string& outputPath, const std::string& genre,
    bool applyMastering, bool applySidechain,
    const std::vector<std::string>& sidechainTargets) {
  try {
    httplib::Client client(host_, port_);
    client.set_read_timeout(120);  // 2 minutes for complex mixing/mastering

    // Build JSON request
    json req;

    // Stems object
    json stemsObj = json::object();
    for (const auto& [name, path] : stems) {
      stemsObj[name] = path;
    }
    req["stems"] = stemsObj;

    req["output_path"] = outputPath;
    req["genre"] = genre;
    req["apply_mastering"] = applyMastering;
    req["apply_sidechain"] = applySidechain;

    // Sidechain targets array
    json targetsArr = json::array();
    for (const auto& target : sidechainTargets) {
      targetsArr.push_back(target);
    }
    req["sidechain_targets"] = targetsArr;

    std::string body = req.dump();

    std::cout << "[AudioProducerClient] Producing track with " << stems.size()
              << " stems..." << std::endl;
    std::cout << "[AudioProducerClient] Genre: " << genre
              << ", Mastering: " << (applyMastering ? "yes" : "no")
              << ", Sidechain: " << (applySidechain ? "yes" : "no")
              << std::endl;

    auto res = client.Post("/produce", body, "application/json");

    if (!res) {
      std::cerr << "[AudioProducerClient] HTTP request failed: "
                << httplib::to_string(res.error()) << std::endl;
      return false;
    }

    if (res->status != 200) {
      std::cerr << "[AudioProducerClient] HTTP error " << res->status << ": "
                << res->body << std::endl;
      return false;
    }

    // Parse response
    json response = json::parse(res->body);

    if (response["status"] == "success") {
      std::cout << "[AudioProducerClient] Success!" << std::endl;

      if (response.contains("lufs")) {
        std::cout << "  LUFS: " << response["lufs"] << std::endl;
      }
      if (response.contains("duration_sec")) {
        std::cout << "  Duration: " << response["duration_sec"] << " sec"
                  << std::endl;
      }
      if (response.contains("stems_count")) {
        std::cout << "  Stems mixed: " << response["stems_count"] << std::endl;
      }

      return true;
    } else {
      std::cerr << "[AudioProducerClient] Service error: "
                << response.value("message", "Unknown error") << std::endl;
      return false;
    }

  } catch (const std::exception& e) {
    std::cerr << "[AudioProducerClient] Exception: " << e.what() << std::endl;
    return false;
  }
}

bool AudioProducerClient::renderStem(const std::string& midiPath,
                                     const std::string& outputPath) {
  try {
    httplib::Client client(host_, port_);
    client.set_read_timeout(60);

    json req;
    req["midi_path"] = midiPath;
    req["output_path"] = outputPath;

    std::string body = req.dump();

    std::cout << "[AudioProducerClient] Rendering stem: " << midiPath
              << std::endl;

    auto res = client.Post("/render-stem", body, "application/json");

    if (!res) {
      std::cerr << "[AudioProducerClient] HTTP request failed: "
                << httplib::to_string(res.error()) << std::endl;
      return false;
    }

    if (res->status != 200) {
      std::cerr << "[AudioProducerClient] HTTP error " << res->status << ": "
                << res->body << std::endl;
      return false;
    }

    json response = json::parse(res->body);

    if (response["status"] == "success") {
      std::cout << "[AudioProducerClient] Stem rendered successfully"
                << std::endl;
      return true;
    } else {
      std::cerr << "[AudioProducerClient] Render failed: "
                << response.value("message", "Unknown error") << std::endl;
      return false;
    }

  } catch (const std::exception& e) {
    std::cerr << "[AudioProducerClient] Exception: " << e.what() << std::endl;
    return false;
  }
}

bool AudioProducerClient::healthCheck() {
  try {
    httplib::Client client(host_, port_);
    client.set_read_timeout(5);

    auto res = client.Get("/health");

    if (!res) {
      return false;
    }

    if (res->status != 200) {
      return false;
    }

    json response = json::parse(res->body);
    return response["status"] == "healthy";

  } catch (...) {
    return false;
  }
}
