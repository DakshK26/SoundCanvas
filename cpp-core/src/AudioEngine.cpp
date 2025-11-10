#include "AudioEngine.hpp"
#include <cmath>
#include <cstdint>
#include <fstream>
#include <stdexcept>

namespace {

constexpr int SAMPLE_RATE = 44100;

// Write little-endian helper
void writeLE(std::ofstream& out, std::uint32_t value, int bytes) {
    for (int i = 0; i < bytes; ++i) {
        out.put(static_cast<char>(value & 0xFF));
        value >>= 8;
    }
}

}  // namespace

void generateAmbientTrack(const std::string& outputPath, const MusicParameters& params) {
    const int numSamples = static_cast<int>(params.durationSeconds * SAMPLE_RATE);

    std::ofstream out(outputPath, std::ios::binary);
    if (!out) {
        throw std::runtime_error("Failed to open output WAV: " + outputPath);
    }

    // --- Write WAV header (PCM 16-bit, mono) ---
    int numChannels = 1;
    int bitsPerSample = 16;
    int byteRate = SAMPLE_RATE * numChannels * bitsPerSample / 8;
    int blockAlign = numChannels * bitsPerSample / 8;
    int dataSize = numSamples * numChannels * bitsPerSample / 8;
    int chunkSize = 36 + dataSize;

    // RIFF header
    out.write("RIFF", 4);
    writeLE(out, chunkSize, 4);
    out.write("WAVE", 4);

    // fmt subchunk
    out.write("fmt ", 4);
    writeLE(out, 16, 4);             // Subchunk1Size
    writeLE(out, 1, 2);              // AudioFormat (PCM)
    writeLE(out, numChannels, 2);    // NumChannels
    writeLE(out, SAMPLE_RATE, 4);    // SampleRate
    writeLE(out, byteRate, 4);       // ByteRate
    writeLE(out, blockAlign, 2);     // BlockAlign
    writeLE(out, bitsPerSample, 2);  // BitsPerSample

    // data subchunk
    out.write("data", 4);
    writeLE(out, dataSize, 4);

    // --- Generate samples ---
    double baseFreq = params.baseFrequency;
    double phase = 0.0;
    double phaseStep = 2.0 * M_PI * baseFreq / SAMPLE_RATE;

    for (int i = 0; i < numSamples; ++i) {
        double t = static_cast<double>(i) / numSamples;

        // Simple fade in/out envelope
        double env = std::sin(M_PI * t);

        // Slight modulation for "ambient" feel
        double mod = 0.5 + 0.5 * std::sin(2.0 * M_PI * t * (params.tempoBpm / 60.0));

        double sampleValue = std::sin(phase) * env * mod * params.volume;

        phase += phaseStep;
        if (phase > 2.0 * M_PI) {
            phase -= 2.0 * M_PI;
        }

        // Convert to 16-bit
        int16_t intSample = static_cast<int16_t>(sampleValue * 32767.0);
        writeLE(out, static_cast<std::uint16_t>(intSample), 2);
    }

    out.close();
    if (!out) {
        throw std::runtime_error("Error while writing WAV file: " + outputPath);
    }
}