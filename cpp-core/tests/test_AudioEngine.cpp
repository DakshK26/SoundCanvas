#include "AudioEngine.hpp"
#include <iostream>
#include <fstream>

// Simple test to verify WAV file generation works
int main() {
    std::cout << "Testing AudioEngine...\n";

    // Create test parameters
    MusicParameters params;
    params.tempoBpm = 60.0f;
    params.baseFrequency = 220.0f;  // A3 note
    params.brightness = 0.5f;
    params.volume = 0.5f;
    params.durationSeconds = 3.0f;

    try {
        // Generate test audio
        generateAmbientTrack("test_output.wav", params);
        
        // Verify file exists and has content
        std::ifstream file("test_output.wav", std::ios::binary | std::ios::ate);
        if (!file) {
            std::cerr << "FAILED: Output file not created\n";
            return 1;
        }
        
        std::streamsize fileSize = file.tellg();
        file.close();
        
        // Expected size: 44 bytes header + (3 seconds * 44100 samples/sec * 2 bytes/sample)
        std::streamsize expectedSize = 44 + (3 * 44100 * 2);
        
        if (fileSize != expectedSize) {
            std::cerr << "FAILED: File size mismatch. Expected " << expectedSize 
                      << " bytes, got " << fileSize << " bytes\n";
            return 1;
        }
        
        std::cout << "PASSED: Generated test_output.wav (" << fileSize << " bytes)\n";
        std::cout << "You can now play test_output.wav to verify audio quality\n";
        
        return 0;
        
    } catch (const std::exception& ex) {
        std::cerr << "FAILED: " << ex.what() << "\n";
        return 1;
    }
}