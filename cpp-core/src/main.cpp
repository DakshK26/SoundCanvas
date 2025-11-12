#include <cstdio>  // for std::remove
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

#include "AudioEngine.hpp"
#include "AudioProducerClient.hpp"  // Phase 8: Production service client
#include "Composer.hpp"             // Phase 7: MIDI generation
#include "GenreTemplate.hpp"        // Phase 8: Genre templates
#include "HttpServer.hpp"
#include "ImageFeatures.hpp"
#include "ModelClient.hpp"
#include "MusicMapping.hpp"
#include "MusicalStyle.hpp"    // Phase 7: Extended style controls
#include "SectionPlanner.hpp"  // Phase 8: Structured composition
#include "SongSpec.hpp"        // Phase 7: Song composition

enum class Mode { Heuristic, Model };

Mode parseMode(const std::string& s) {
  if (s == "heuristic") return Mode::Heuristic;
  if (s == "model") return Mode::Model;
  throw std::runtime_error("Unknown mode: " + s +
                           " (expected 'heuristic' or 'model')");
}

// Helper to get environment variable or return default
static std::string getEnvOrDefault(const char* key,
                                   const std::string& defaultValue) {
  const char* val = std::getenv(key);
  return val ? std::string(val) : defaultValue;
}

int main(int argc, char** argv) {
  // Check for server mode first
  if (argc >= 2 && std::string(argv[1]) == "--serve") {
    // HTTP server mode
    std::string defaultMode = getEnvOrDefault("SC_DEFAULT_MODE", "model");
    std::string outputDir = getEnvOrDefault("SC_OUTPUT_DIR", "../examples");

    int port = 8080;
    const char* portEnv = std::getenv("SC_HTTP_PORT");
    if (portEnv) {
      try {
        port = std::stoi(portEnv);
      } catch (...) {
        std::cerr << "Invalid SC_HTTP_PORT value, using default 8080"
                  << std::endl;
      }
    }

    std::cout << "Starting HTTP server mode..." << std::endl;
    std::cout << "  Port: " << port << std::endl;
    std::cout << "  Default mode: " << defaultMode << std::endl;
    std::cout << "  Output directory: " << outputDir << std::endl;

    try {
      runHttpServer(port, defaultMode, outputDir);
      return 0;
    } catch (const std::exception& ex) {
      std::cerr << "Failed to start HTTP server: " << ex.what() << std::endl;
      return 1;
    }
  }

  // Phase 7: Check for --compose-only mode
  if (argc >= 4 && std::string(argv[1]) == "--compose-only") {
    std::string inputImage = argv[2];
    std::string outputMidi = argv[3];

    try {
      std::cout << "MIDI Composition Mode\n";
      std::cout << "=====================\n";
      std::cout << "Reading image: " << inputImage << std::endl;

      // Extract features
      ImageFeatures features = extractImageFeatures(inputImage);

      // Get music parameters (use model if available, else heuristic)
      MusicParameters params;
      std::string tfUrl = getEnvOrDefault(
          "SC_TF_SERVING_URL",
          "http://localhost:8501/v1/models/soundcanvas:predict");

      try {
        ModelClient client(tfUrl);
        params = mapFeaturesToMusicModel(features, client);
        std::cout << "Using ML model for parameters\n";
      } catch (...) {
        params = mapFeaturesToMusicHeuristic(features);
        std::cout << "Using heuristic mapping (model unavailable)\n";
      }

      // Create song spec
      SongSpec songSpec = makeSongSpec(features, params);

      // Display song structure
      std::cout << "\nSong Specification:\n";
      std::cout << "  Genre: " << genreName(songSpec.genreProfile.genre) << "\n";
      std::cout << "  Tempo: " << songSpec.tempoBpm << " BPM\n";
      std::cout << "  Key: MIDI " << songSpec.rootMidiNote << "\n";
      std::cout << "  Scale: "
                << (songSpec.scaleType == 0   ? "Major"
                    : songSpec.scaleType == 1 ? "Minor"
                    : songSpec.scaleType == 2 ? "Dorian"
                                              : "Lydian")
                << "\n";
      std::cout << "  Total bars: " << songSpec.totalBars << "\n";
      std::cout << "  Groove: " << grooveTypeName(songSpec.groove);
      if (songSpec.genreProfile.useSwing) {
        std::cout << " (swing: " << (int)(songSpec.genreProfile.swingAmount * 100) << "%)";
      }
      std::cout << "\n";
      std::cout << "  Ambience: " << ambienceTypeName(songSpec.ambience)
                << "\n";
      std::cout << "  Mood: " << songSpec.moodScore << "\n";

      std::cout << "\nSections:\n";
      for (const auto& section : songSpec.sections) {
        std::cout << "  " << section.name << ": " << section.bars
                  << " bars (energy: " << section.targetEnergy << ")\n";
      }

      std::cout << "\nTracks:\n";
      for (const auto& track : songSpec.tracks) {
        std::cout << "  " << trackRoleName(track.role) << ": "
                  << "program " << track.program
                  << " (channel " << track.midiChannel << ")"
                  << " vol=" << track.baseVolume
                  << " complexity=" << track.complexity << "\n";
      }

      // Compose to MIDI
      std::cout << "\nComposing MIDI...\n";
      composeSongToMidi(songSpec, outputMidi);
      std::cout << "Wrote MIDI to: " << outputMidi << std::endl;
      std::cout << "\nTip: Load this file in a DAW or play with:\n";
      std::cout << "  fluidsynth -a alsa soundfont.sf2 " << outputMidi
                << std::endl;

      return 0;
    } catch (const std::exception& ex) {
      std::cerr << "Error: " << ex.what() << std::endl;
      return 1;
    }
  }

  // Phase 8: Full pipeline mode (Person A + Person B)
  if (argc >= 4 && std::string(argv[1]) == "--full-pipeline") {
    std::string inputImage = argv[2];
    std::string outputWav = argv[3];
    std::string stemsDir = argc >= 5 ? argv[4] : "/tmp/soundcanvas_stems";

    try {
      std::cout << "===========================================\n";
      std::cout << "Full Pipeline: Image → MIDI Stems → Mastered WAV\n";
      std::cout << "===========================================\n\n";

      // Step 1: Extract features
      std::cout << "[1/4] Extracting image features...\n";
      ImageFeatures features = extractImageFeatures(inputImage);

      // Step 2: Get music parameters
      std::cout << "[2/4] Generating musical parameters...\n";
      MusicParameters params;
      std::string tfUrl = getEnvOrDefault(
          "SC_TF_SERVING_URL",
          "http://localhost:8501/v1/models/soundcanvas:predict");

      try {
        ModelClient client(tfUrl);
        params = mapFeaturesToMusicModel(features, client);
      } catch (...) {
        params = mapFeaturesToMusicHeuristic(features);
      }

      // Create song spec
      SongSpec songSpec = makeSongSpec(features, params);

      std::cout << "  Genre: " << genreName(songSpec.genreProfile.genre) << "\n";
      std::cout << "  Tempo: " << songSpec.tempoBpm << " BPM\n";
      std::cout << "  Key: " << songSpec.rootMidiNote << "\n";
      std::cout << "  Mood: " << songSpec.moodScore << "\n";

      // Step 3: Compose separate MIDI stems (Person A)
      std::cout << "[3/4] Composing separate MIDI stems...\n";
      auto stemFiles = composeSongToStems(songSpec, stemsDir);

      std::cout << "  Generated " << stemFiles.size() << " stem files:\n";
      for (const auto& [name, path] : stemFiles) {
        std::cout << "    " << name << ": " << path << "\n";
      }

      // Step 4: Call audio-producer service (Person B)
      std::cout << "[4/4] Professional mixing & mastering...\n";

      std::string producerUrl =
          getEnvOrDefault("SC_AUDIO_PRODUCER_URL", "http://localhost:9001");

      AudioProducerClient producer(producerUrl);

      if (!producer.healthCheck()) {
        std::cerr << "\n⚠️  Warning: audio-producer service not available at "
                  << producerUrl << "\n";
        std::cerr << "  Falling back to basic FluidSynth rendering...\n\n";
        std::cerr << "To use full production pipeline:\n";
        std::cerr << "  cd infra && docker-compose up audio-producer -d\n\n";

        // Fallback: Just use the first stem or combined MIDI
        std::cerr
            << "Using basic rendering instead of professional production.\n";
        return 1;
      }

      bool success = producer.produceTrack(
          stemFiles, outputWav,
          "EDM_" + std::string(static_cast<int>(songSpec.groove) == 1
                                   ? "Drop"
                                   : "Chill"),
          true,  // apply mastering
          true,  // apply sidechain
          {"bass", "chords", "melody", "pad"});

      if (success) {
        std::cout << "\n✅ Full pipeline complete!\n";
        std::cout << "   Output: " << outputWav << "\n";
        std::cout << "   Quality: Professional (-14 LUFS, mastered)\n";
        std::cout << "   Features: Multi-stem mix, sidechain, EQ, compression, "
                     "limiting\n";
        std::cout << "\nPlay with: afplay " << outputWav << "\n";
        return 0;
      } else {
        std::cerr << "Production failed.\n";
        return 1;
      }

    } catch (const std::exception& ex) {
      std::cerr << "Error: " << ex.what() << std::endl;
      return 1;
    }
  }

  // CLI mode (existing Phase 3 behavior)
  // Usage:
  //   soundcanvas_core <input_image> <output_wav>                          →
  //   heuristic mode (default) soundcanvas_core --mode=<heuristic|model>
  //   <input_image> <output_wav> → explicit mode

  if (argc < 3 || argc > 4) {
    std::cerr << "Usage:\n"
              << "  soundcanvas_core --serve                                   "
                 "           → HTTP server mode\n"
              << "  soundcanvas_core --compose-only <input_image> "
                 "<output_midi>           → MIDI composition only\n"
              << "  soundcanvas_core --full-pipeline <input_image> "
                 "<output_wav> [stems_dir] → Full production pipeline\n"
              << "  soundcanvas_core <input_image> <output_wav>                "
                 "           → CLI heuristic mode\n"
              << "  soundcanvas_core --mode=<heuristic|model> <input_image> "
                 "<output_wav>  → CLI with mode\n";
    return 1;
  }

  Mode mode = Mode::Heuristic;
  std::string inputImage;
  std::string outputWav;

  if (argc == 3) {
    // Default: heuristic mode (backward compatible)
    inputImage = argv[1];
    outputWav = argv[2];
  } else {
    // argc == 4: parse --mode=...
    std::string modeArg = argv[1];
    const std::string prefix = "--mode=";
    if (modeArg.rfind(prefix, 0) != 0) {
      std::cerr << "Invalid first argument: " << modeArg << std::endl;
      return 1;
    }
    mode = parseMode(modeArg.substr(prefix.size()));
    inputImage = argv[2];
    outputWav = argv[3];
  }

  try {
    std::cout << "Reading image: " << inputImage << std::endl;
    ImageFeatures features = extractImageFeatures(inputImage);

    std::cout << "Image features (8-dim):\n"
              << "  avgR         = " << features.avgR << "\n"
              << "  avgG         = " << features.avgG << "\n"
              << "  avgB         = " << features.avgB << "\n"
              << "  brightness   = " << features.brightness << "\n"
              << "  hue          = " << features.hue << "\n"
              << "  saturation   = " << features.saturation << "\n"
              << "  colorfulness = " << features.colorfulness << "\n"
              << "  contrast     = " << features.contrast << std::endl;

    MusicParameters params;

    if (mode == Mode::Heuristic) {
      std::cout << "Using heuristic mapping.\n";
      params = mapFeaturesToMusicHeuristic(features);
    } else {
      std::cout << "Using model mapping via TF Serving.\n";

      // Get TF Serving URL from environment variable or use default
      std::string baseUrl = getEnvOrDefault(
          "SC_TF_SERVING_URL",
          "http://localhost:8501/v1/models/soundcanvas:predict");

      std::cout << "TF Serving URL: " << baseUrl << std::endl;

      ModelClient client(baseUrl);
      params = mapFeaturesToMusicModel(features, client);
    }

    // Map scale and pattern types to human-readable names
    const char* scaleNames[] = {"Major", "Minor", "Dorian", "Lydian"};
    const char* patternNames[] = {"Pad", "Arp", "Chords"};

    const char* scaleName = (params.scaleType >= 0 && params.scaleType <= 3)
                                ? scaleNames[params.scaleType]
                                : "Unknown";
    const char* patternName =
        (params.patternType >= 0 && params.patternType <= 2)
            ? patternNames[params.patternType]
            : "Unknown";

    std::cout << "Music parameters (7-dim):\n"
              << "  tempoBpm      = " << params.tempoBpm << " BPM\n"
              << "  baseFrequency = " << params.baseFrequency << " Hz\n"
              << "  energy        = " << params.energy << "\n"
              << "  brightness    = " << params.brightness << "\n"
              << "  reverb        = " << params.reverb << "\n"
              << "  scaleType     = " << params.scaleType << " (" << scaleName
              << ")\n"
              << "  patternType   = " << params.patternType << " ("
              << patternName << ")" << std::endl;

    // Phase 7: Derive extended style controls
    StyleParameters style = deriveStyle(features, params);

    std::cout << "Style parameters (Phase 7):\n"
              << "  ambienceType      = "
              << ambienceTypeName(style.ambienceType) << "\n"
              << "  instrumentPreset  = "
              << instrumentPresetName(style.instrumentPreset) << "\n"
              << "  moodScore         = " << style.moodScore << " (lushness)"
              << std::endl;

    // Phase 8: Select genre and create structured song plan
    GenreType genre = selectGenreFromImage(features, params.energy);
    const GenreTemplate& genreTemplate = getGenreTemplate(genre);

    std::cout << "\n=== Phase 8: Genre-Based Composition ===\n"
              << "Selected genre: " << genreTypeName(genre) << "\n"
              << "Tempo range: " << genreTemplate.minTempo << "-"
              << genreTemplate.maxTempo << " BPM" << std::endl;

    SongPlan plan = planSong(features, params, genreTemplate);

    std::cout << "\nSong Plan:\n"
              << "  Genre: " << genreTypeName(plan.genre) << "\n"
              << "  Tempo: " << plan.tempoBpm << " BPM\n"
              << "  Key: MIDI " << plan.rootNote << " (" << scaleName << ")\n"
              << "  Total bars: " << plan.totalBars << "\n"
              << "  Sections: " << plan.sections.size() << "\n"
              << "  Active instruments: " << plan.activeInstruments.size()
              << std::endl;

    std::cout << "\nSection Timeline:\n";
    for (const auto& sec : plan.sections) {
      std::cout << "  " << sectionTypeName(sec.type) << ": bars "
                << sec.startBar << "-" << (sec.startBar + sec.bars)
                << " (energy: " << sec.energy << ")";
      if (sec.hasDrop) std::cout << " [DROP!]";
      std::cout << std::endl;
    }

    // Generate intermediate MIDI file
    std::string tempMidi = outputWav + ".tmp.mid";
    std::cout << "\nComposing MIDI to: " << tempMidi << std::endl;
    composeGenreSongToMidi(plan, tempMidi);

    // Render MIDI to WAV using FluidSynth
    std::string soundfont = "/usr/share/sounds/sf2/FluidR3_GM.sf2";
    std::cout << "Rendering MIDI to WAV using FluidSynth..." << std::endl;

    std::string fluidCmd = "fluidsynth -ni -g 0.8 -F \"" + outputWav + "\" \"" +
                           soundfont + "\" \"" + tempMidi + "\" 2>&1";
    int result = std::system(fluidCmd.c_str());

    if (result != 0) {
      std::cerr << "Warning: FluidSynth returned non-zero exit code: " << result
                << std::endl;
    }

    // Clean up temporary MIDI file
    std::remove(tempMidi.c_str());

    std::cout << "Wrote audio to: " << outputWav << std::endl;

    return 0;
  } catch (const std::exception& ex) {
    std::cerr << "Error: " << ex.what() << std::endl;
    return 1;
  }
}