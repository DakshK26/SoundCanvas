#pragma once
#include <string>

struct MusicParameters {
    float tempoBpm;        // 40–90 BPM (slow ambient range)
    float baseFrequency;   // 100–400 Hz (bass to mid range)
    float energy;          // 0–1 (texture density/busyness)
    float brightness;      // 0–1 (filter cutoff, waveform choice)
    float reverb;          // 0–1 (dry to big hall)
    int   scaleType;       // 0=major, 1=minor, 2=dorian, 3=lydian
    int   patternType;     // 0=pad, 1=arp, 2=chords
};

// Generates a mono WAV file (16-bit PCM, 44.1kHz) with ambient audio
void generateAmbientTrack(const std::string& outputPath,
                          const MusicParameters& params);