#include "HttpServer.hpp"

#include "httplib.h"
#include "json.hpp"

#include "ImageFeatures.hpp"
#include "MusicMapping.hpp"
#include "ModelClient.hpp"
#include "AudioEngine.hpp"
#include "MusicalStyle.hpp"  // Phase 7
#include "GenreTemplate.hpp"  // Phase 12: Genre selection
#include "SectionPlanner.hpp" // Phase 12: Song planning
#include "Composer.hpp"       // Phase 12: Genre-based composition

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <stdexcept>

using json = nlohmann::json;
namespace fs = std::filesystem;

static std::string getEnvOrDefault(const char* key, const std::string& def) {
    const char* v = std::getenv(key);
    return v ? std::string(v) : def;
}

void runHttpServer(
    int port,
    const std::string& defaultMode,
    const std::string& outputDir
) {
    httplib::Server svr;

    // Ensure output directory exists
    fs::create_directories(outputDir);

    svr.Post("/generate", [defaultMode, outputDir](const httplib::Request& req, httplib::Response& res) {
        try {
            if (req.body.empty()) {
                res.status = 400;
                res.set_content("Missing request body", "text/plain");
                return;
            }

            json body = json::parse(req.body);
            if (!body.contains("image_path") || !body["image_path"].is_string()) {
                res.status = 400;
                res.set_content("Missing or invalid 'image_path'", "text/plain");
                return;
            }

            std::string imagePath = body["image_path"].get<std::string>();
            std::string mode = defaultMode;
            if (body.contains("mode") && body["mode"].is_string()) {
                mode = body["mode"].get<std::string>();
            }

            std::cout << "[HTTP] /generate image_path=" << imagePath
                      << " mode=" << mode << std::endl;

            // Extract features
            ImageFeatures features = extractImageFeatures(imagePath);

            // Choose mapping
            MusicParameters params;
            if (mode == "heuristic") {
                params = mapFeaturesToMusicHeuristic(features);
            } else if (mode == "model") {
                std::string tfUrl = getEnvOrDefault(
                    "SC_TF_SERVING_URL",
                    "http://localhost:8501/v1/models/soundcanvas:predict"
                );
                ModelClient client(tfUrl);
                params = mapFeaturesToMusicModel(features, client);
            } else {
                res.status = 400;
                res.set_content("Unknown mode (expected 'heuristic' or 'model')", "text/plain");
                return;
            }

            // Output filename
            auto now = std::chrono::system_clock::now().time_since_epoch();
            auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(now).count();
            std::string filename = "sound_" + std::to_string(millis) + ".wav";
            fs::path outPath = fs::path(outputDir) / filename;

            // Phase 7: Derive extended style parameters
            StyleParameters style = deriveStyle(features, params);

            // Phase 12 A2.2: Select genre from image and create MIDI
            GenreType decidedGenre = selectGenreFromImage(features, params.energy);
            const GenreTemplate& genreTemplate = getGenreTemplate(decidedGenre);
            
            std::cout << "[HTTP] Selected genre: " << genreTypeName(decidedGenre) 
                      << " (tempo range: " << genreTemplate.minTempo << "-" 
                      << genreTemplate.maxTempo << " BPM)" << std::endl;

            // Plan song structure
            SongPlan plan = planSong(features, params, genreTemplate);
            
            // Generate MIDI file
            std::string midiFilename = "composition_" + std::to_string(millis) + ".mid";
            fs::path midiPath = fs::path(outputDir) / midiFilename;
            
            std::cout << "[HTTP] Composing MIDI to: " << midiPath << std::endl;
            composeGenreSongToMidi(plan, midiPath.string());
            
            // Scale type string
            const char* scaleNames[] = {"Major", "Minor", "Dorian", "Lydian"};
            const char* scaleTypeStr = (params.scaleType >= 0 && params.scaleType <= 3)
                                        ? scaleNames[params.scaleType]
                                        : "Unknown";

            // Build JSON response with new 7-dim parameters + decided genre
            json resp;
            resp["midi_path"] = midiPath.string();  // Phase 12: Return MIDI path instead of WAV
            resp["audio_path"] = outPath.string();  // Keep for backward compatibility
            resp["decided_genre"] = genreTypeName(decidedGenre);  // Phase 12 A2.2: Return decided genre!
            resp["tempo_bpm"] = plan.tempoBpm;
            resp["scale_type"] = scaleTypeStr;
            resp["params"] = {
                {"tempoBpm",      params.tempoBpm},
                {"baseFrequency", params.baseFrequency},
                {"energy",        params.energy},
                {"brightness",    params.brightness},
                {"reverb",        params.reverb},
                {"scaleType",     params.scaleType},
                {"patternType",   params.patternType}
            };

            res.status = 200;
            res.set_content(resp.dump(), "application/json");
        } catch (const std::exception& ex) {
            std::cerr << "[HTTP] Error in /generate: " << ex.what() << std::endl;
            res.status = 500;
            res.set_content(std::string("Internal server error: ") + ex.what(), "text/plain");
        }
    });

    std::cout << "[HTTP] Server starting on port " << port
              << " (defaultMode=" << defaultMode
              << ", outputDir=" << outputDir << ")" << std::endl;

    if (!svr.listen("0.0.0.0", port)) {
        throw std::runtime_error("Failed to start HTTP server on port " + std::to_string(port));
    }
}
