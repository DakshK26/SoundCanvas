#include "AudioRendererClient.hpp"

#include <iostream>
#include <stdexcept>

#include "AudioEngine.hpp"
#include "httplib.h"
#include "json.hpp"

using json = nlohmann::json;

AudioRendererClient::AudioRendererClient(const std::string& baseUrl)
    : baseUrl_(baseUrl) {}

bool AudioRendererClient::renderMidiToWav(const std::string& midiPath,
                                          const std::string& outputPath,
                                          const StyleParameters& style) const {
  try {
    // Parse base URL to extract host and port
    std::string host = baseUrl_;
    int port = 9000;

    // Simple URL parsing (assumes http://host:port format)
    if (host.find("http://") == 0) {
      host = host.substr(7);
    }

    size_t colonPos = host.find(':');
    if (colonPos != std::string::npos) {
      port = std::stoi(host.substr(colonPos + 1));
      host = host.substr(0, colonPos);
    }

    std::cout << "[INFO] Connecting to audio renderer: " << host << ":" << port
              << std::endl;

    httplib::Client cli(host, port);
    cli.set_connection_timeout(5, 0);  // 5 seconds
    cli.set_read_timeout(60, 0);       // 60 seconds for rendering

    // Map ambience type to string
    const char* ambienceTypes[] = {"none", "ocean", "rain", "forest", "city"};
    std::string ambienceStr = "none";
    if (style.ambienceType >= 0 && style.ambienceType <= 4) {
      ambienceStr = ambienceTypes[style.ambienceType];
    }

    // Build request JSON
    json request = {{"midi_path", midiPath},
                    {"output_path", outputPath},
                    {"ambience_type", ambienceStr},
                    {"mood_score", style.moodScore}};

    std::cout << "[INFO] Rendering MIDI: " << midiPath << std::endl;
    std::cout << "[INFO]   Ambience: " << ambienceStr
              << ", Mood: " << style.moodScore << std::endl;

    // Send POST request
    auto res = cli.Post("/render", request.dump(), "application/json");

    if (!res) {
      std::cerr << "[ERROR] Failed to connect to audio renderer service"
                << std::endl;
      return false;
    }

    if (res->status != 200) {
      std::cerr << "[ERROR] Audio renderer returned status " << res->status
                << std::endl;
      std::cerr << "[ERROR] Response: " << res->body << std::endl;
      return false;
    }

    // Parse response
    json response = json::parse(res->body);

    if (response["status"] == "success") {
      std::cout << "[INFO] Audio rendered successfully: " << outputPath
                << std::endl;
      if (response.contains("file_size")) {
        std::cout << "[INFO]   File size: " << response["file_size"] << " bytes"
                  << std::endl;
      }
      return true;
    } else {
      std::cerr << "[ERROR] Rendering failed: " << response.dump() << std::endl;
      return false;
    }

  } catch (const std::exception& e) {
    std::cerr << "[ERROR] Exception during audio rendering: " << e.what()
              << std::endl;
    return false;
  }
}
