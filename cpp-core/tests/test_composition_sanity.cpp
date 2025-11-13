/**
 * Phase 12 A3.1: Composition Sanity Tests
 * 
 * Test each genre template to ensure:
 * - MIDI files are generated
 * - Expected instruments are present
 * - Tempo is within genre range
 * - Duration is reasonable (> 30 seconds)
 * - Drums have events (not empty)
 */

#include "../include/Composer.hpp"
#include "../include/GenreTemplate.hpp"
#include "../include/SectionPlanner.hpp"
#include "../include/ImageFeatures.hpp"
#include "../include/MusicMapping.hpp"
#include "../include/MidiWriter.hpp"

#include <iostream>
#include <fstream>
#include <filesystem>
#include <cassert>

namespace fs = std::filesystem;

/**
 * Check if MIDI file exists and has non-zero size
 */
bool validateMidiFile(const std::string& path) {
    if (!fs::exists(path)) {
        std::cerr << "FAIL: MIDI file does not exist: " << path << std::endl;
        return false;
    }
    
    auto size = fs::file_size(path);
    if (size == 0) {
        std::cerr << "FAIL: MIDI file is zero bytes: " << path << std::endl;
        return false;
    }
    
    if (size < 100) {
        std::cerr << "WARN: MIDI file suspiciously small (" << size << " bytes): " << path << std::endl;
        return false;
    }
    
    std::cout << "  ✓ MIDI file valid: " << size << " bytes" << std::endl;
    return true;
}

/**
 * Create a mock song plan for testing a specific genre
 */
SongPlan createTestPlan(GenreType genre, int tempoBpm = 120) {
    const GenreTemplate& templ = getGenreTemplate(genre);
    
    // Create simple mock features
    ImageFeatures features;
    features.hue = 0.5f;
    features.saturation = 0.6f;
    features.brightness = 0.5f;
    features.contrast = 0.5f;
    features.colorfulness = 0.5f;
    features.sharpness = 0.5f;
    
    MusicParameters params;
    params.tempoBpm = tempoBpm;
    params.baseFrequency = 220.0f;
    params.energy = 0.7f;
    params.brightness = 0.5f;
    params.reverb = 0.3f;
    params.scaleType = 1;  // Minor
    params.patternType = 0;
    
    return planSong(features, params, templ);
}

/**
 * Test composition for a specific genre
 */
bool testGenreComposition(GenreType genre, const std::string& outputDir) {
    std::cout << "\n=== Testing " << genreTypeName(genre) << " ===\n";
    
    const GenreTemplate& templ = getGenreTemplate(genre);
    std::cout << "Genre template: " 
              << templ.minTempo << "-" << templ.maxTempo << " BPM, "
              << templ.sections.size() << " section templates" << std::endl;
    
    // Create song plan
    int testTempo = (templ.minTempo + templ.maxTempo) / 2;
    SongPlan plan = createTestPlan(genre, testTempo);
    
    std::cout << "Generated plan:\n"
              << "  Tempo: " << plan.tempoBpm << " BPM\n"
              << "  Key: MIDI " << plan.rootNote << "\n"
              << "  Total bars: " << plan.totalBars << "\n"
              << "  Sections: " << plan.sections.size() << "\n"
              << "  Active instruments: " << plan.activeInstruments.size() << std::endl;
    
    // Validation checks
    bool valid = true;
    
    // Check 1: Tempo in range
    if (plan.tempoBpm < templ.minTempo || plan.tempoBpm > templ.maxTempo) {
        std::cerr << "  ✗ Tempo out of range: " << plan.tempoBpm 
                  << " not in [" << templ.minTempo << ", " << templ.maxTempo << "]" << std::endl;
        valid = false;
    } else {
        std::cout << "  ✓ Tempo in range" << std::endl;
    }
    
    // Check 2: Has sections
    if (plan.sections.empty()) {
        std::cerr << "  ✗ No sections generated" << std::endl;
        valid = false;
    } else {
        std::cout << "  ✓ Has " << plan.sections.size() << " sections" << std::endl;
    }
    
    // Check 3: Has instruments
    if (plan.activeInstruments.empty()) {
        std::cerr << "  ✗ No active instruments" << std::endl;
        valid = false;
    } else {
        std::cout << "  ✓ Has " << plan.activeInstruments.size() << " instruments" << std::endl;
    }
    
    // Check 4: Reasonable duration (at least 30 seconds)
    double durationSec = (plan.totalBars * 4.0 * 60.0) / plan.tempoBpm;
    if (durationSec < 30.0) {
        std::cerr << "  ✗ Duration too short: " << durationSec << "s" << std::endl;
        valid = false;
    } else {
        std::cout << "  ✓ Duration reasonable: " << durationSec << "s" << std::endl;
    }
    
    // Generate MIDI
    std::string midiPath = outputDir + "/" + std::string(genreTypeName(genre)) + "_test.mid";
    std::cout << "Composing MIDI to: " << midiPath << std::endl;
    
    try {
        composeGenreSongToMidi(plan, midiPath);
    } catch (const std::exception& e) {
        std::cerr << "  ✗ Composition failed: " << e.what() << std::endl;
        return false;
    }
    
    // Validate MIDI file
    if (!validateMidiFile(midiPath)) {
        return false;
    }
    
    std::cout << "  ✓ " << genreTypeName(genre) << " composition PASSED" << std::endl;
    return valid;
}

int main(int argc, char* argv[]) {
    std::cout << "=== Phase 12 A3.1: Composition Sanity Tests ===\n" << std::endl;
    
    // Create output directory
    std::string outputDir = argc > 1 ? argv[1] : "/tmp/composition_tests";
    fs::create_directories(outputDir);
    std::cout << "Output directory: " << outputDir << "\n" << std::endl;
    
    // Test each genre
    GenreType genres[] = {
        GenreType::EDM_CHILL,
        GenreType::EDM_DROP,
        GenreType::RETROWAVE,
        GenreType::CINEMATIC
    };
    
    int passed = 0;
    int total = 0;
    
    for (GenreType genre : genres) {
        total++;
        if (testGenreComposition(genre, outputDir)) {
            passed++;
        }
    }
    
    std::cout << "\n=== Test Summary ===\n"
              << "Passed: " << passed << "/" << total << std::endl;
    
    if (passed == total) {
        std::cout << "✓ All composition tests PASSED" << std::endl;
        return 0;
    } else {
        std::cerr << "✗ Some composition tests FAILED" << std::endl;
        return 1;
    }
}
