#include "AudioEngine.hpp"
#include <cmath>
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <vector>
#include <algorithm>
#include <iostream>
#include <random>

namespace {

constexpr int SAMPLE_RATE = 44100;

// Write little-endian helper
void writeLE(std::ofstream& out, std::uint32_t value, int bytes) {
    for (int i = 0; i < bytes; ++i) {
        out.put(static_cast<char>(value & 0xFF));
        value >>= 8;
    }
}

// === Phase 7: Instrument Preset Enums ===
enum InstrumentPreset {
    SOFT_PAD = 0,
    SOFT_KEYS = 1,
    PLUCK = 2,
    BELL = 3
};

// === Phase 7: Simple WAV file loader ===
struct AmbienceBuffer {
    std::vector<float> samples;
    bool loaded = false;
};

// Global cache for ambience samples
static std::vector<AmbienceBuffer> ambienceCache(5);  // 5 ambience types

// Load a WAV file into memory (simplified - assumes 16-bit PCM, 44.1kHz)
bool loadWAVFile(const std::string& filepath, std::vector<float>& outSamples) {
    std::ifstream file(filepath, std::ios::binary);
    if (!file) {
        return false;
    }

    // Read and verify RIFF header
    char riff[4];
    file.read(riff, 4);
    if (std::string(riff, 4) != "RIFF") return false;

    file.seekg(8);  // Skip chunk size and RIFF type
    char wave[4];
    file.read(wave, 4);
    if (std::string(wave, 4) != "WAVE") return false;

    // Find data chunk
    while (file) {
        char chunkId[4];
        file.read(chunkId, 4);
        uint32_t chunkSize;
        file.read(reinterpret_cast<char*>(&chunkSize), 4);

        if (std::string(chunkId, 4) == "data") {
            // Read audio data (assume 16-bit PCM)
            int numSamples = chunkSize / 2;
            outSamples.resize(numSamples);

            for (int i = 0; i < numSamples; ++i) {
                int16_t sample;
                file.read(reinterpret_cast<char*>(&sample), 2);
                outSamples[i] = static_cast<float>(sample) / 32768.0f;
            }
            return true;
        } else {
            // Skip this chunk
            file.seekg(chunkSize, std::ios::cur);
        }
    }

    return false;
}

// Get ambience sample (with looping)
float getAmbienceSample(int ambienceType, int sampleIndex) {
    if (ambienceType < 0 || ambienceType >= 5) return 0.0f;

    // Lazy load ambience files
    if (!ambienceCache[ambienceType].loaded) {
        const std::string basePath = "assets/ambience/";
        std::string filename;

        switch (ambienceType) {
            case 0: filename = "room.wav"; break;
            case 1: filename = "ocean.wav"; break;
            case 2: filename = "rain.wav"; break;
            case 3: filename = "forest.wav"; break;
            case 4: filename = "city.wav"; break;
        }

        std::string fullPath = basePath + filename;
        bool success = loadWAVFile(fullPath, ambienceCache[ambienceType].samples);

        if (!success) {
            std::cerr << "[WARN] Could not load ambience: " << fullPath 
                      << ". Generating procedural fallback.\n";
            
            // Generate simple procedural noise as fallback
            ambienceCache[ambienceType].samples.resize(SAMPLE_RATE * 5);  // 5 seconds
            std::mt19937 rng(ambienceType);
            std::uniform_real_distribution<float> dist(-0.05f, 0.05f);
            
            for (size_t i = 0; i < ambienceCache[ambienceType].samples.size(); ++i) {
                ambienceCache[ambienceType].samples[i] = dist(rng);
            }
        }

        ambienceCache[ambienceType].loaded = true;
    }

    const auto& buffer = ambienceCache[ambienceType].samples;
    if (buffer.empty()) return 0.0f;

    // Loop the sample
    int index = sampleIndex % static_cast<int>(buffer.size());
    return buffer[index];
}

// Musical scale intervals in semitones
static std::vector<int> getScaleSemitones(int scaleType) {
    switch (scaleType) {
        case 0: return {0, 2, 4, 5, 7, 9, 11};      // Major
        case 1: return {0, 2, 3, 5, 7, 8, 10};      // Minor
        case 2: return {0, 2, 3, 5, 7, 9, 10};      // Dorian
        case 3: 
        default: return {0, 2, 4, 6, 7, 9, 11};     // Lydian
    }
}

// MIDI conversion helpers
static double baseFreqToMidi(double freq) {
    return 69.0 + 12.0 * std::log2(freq / 440.0);
}

static double midiToFreq(double midi) {
    return 440.0 * std::pow(2.0, (midi - 69.0) / 12.0);
}

static double getScaleNoteFreq(double baseFreq, const std::vector<int>& scale, int degree) {
    double baseMidi = baseFreqToMidi(baseFreq);
    int semitones = scale[degree % scale.size()];
    int octaves = degree / static_cast<int>(scale.size());
    double noteMidi = baseMidi + semitones + (octaves * 12);
    return midiToFreq(noteMidi);
}

// === Phase 7: Instrument-specific oscillators ===
double instrumentOscillator(InstrumentPreset preset, double phase, double brightness) {
    switch (preset) {
        case SOFT_PAD: {
            // Soft pad: sine + subtle triangle blend, warm and sustained
            double sine = std::sin(phase);
            double triangle = std::asin(std::sin(phase)) * (2.0 / M_PI);
            return sine * 0.7 + triangle * 0.3 * brightness;
        }

        case SOFT_KEYS: {
            // Soft piano-ish: sine + bit of square for body
            double sine = std::sin(phase);
            double square = (phase < M_PI) ? 1.0 : -1.0;
            return sine * 0.8 + square * 0.2 * brightness;
        }

        case PLUCK: {
            // Pluck/harp: bright saw/triangle with quick decay character
            double saw = (phase / M_PI) - 1.0;  // -1 to 1 sawtooth
            double triangle = std::asin(std::sin(phase)) * (2.0 / M_PI);
            return saw * brightness + triangle * (1.0 - brightness * 0.5);
        }

        case BELL: {
            // Bell: additive synthesis with inharmonic partials
            double fund = std::sin(phase);
            double partial2 = std::sin(phase * 2.4) * 0.5;
            double partial3 = std::sin(phase * 3.0) * 0.3;
            return fund + partial2 * brightness + partial3 * brightness;
        }

        default:
            return std::sin(phase);
    }
}

// Context structure for pattern synthesis
struct SynthContext {
    double t;
    const MusicParameters& params;
    const StyleParameters& style;
    const std::vector<int>& scale;
    double secondsPerBeat;
    std::vector<double>& phases;
};

// === Phase 7: Pattern synthesis with instrument presets and mood ===

static double synthPadSample(SynthContext& ctx) {
    InstrumentPreset preset = static_cast<InstrumentPreset>(ctx.style.instrumentPreset);
    
    // Number of notes influenced by energy and mood
    int numNotes = 1 + static_cast<int>(ctx.params.energy * 2.0);
    numNotes = std::min(numNotes, 3);
    
    // Slower LFO for pads
    double lfoFreq = ctx.params.tempoBpm / 240.0;
    double lfo = 0.8 + 0.2 * std::sin(2.0 * M_PI * lfoFreq * ctx.t);
    
    // Mood affects LFO depth (higher mood = more modulation)
    lfo = 1.0 - ctx.style.moodScore * (1.0 - lfo);
    
    double sample = 0.0;
    std::vector<int> degrees = {0, 2, 4};
    
    for (int i = 0; i < numNotes; ++i) {
        double freq = getScaleNoteFreq(ctx.params.baseFrequency, ctx.scale, degrees[i]);
        double phaseStep = 2.0 * M_PI * freq / SAMPLE_RATE;
        
        double noteValue = instrumentOscillator(preset, ctx.phases[i], ctx.params.brightness);
        sample += noteValue * lfo / static_cast<double>(numNotes);
        
        ctx.phases[i] += phaseStep;
        if (ctx.phases[i] > 2.0 * M_PI) ctx.phases[i] -= 2.0 * M_PI;
    }
    
    return sample * (0.5 + 0.3 * ctx.style.moodScore);  // Louder for higher mood
}

static double synthArpSample(SynthContext& ctx) {
    InstrumentPreset preset = static_cast<InstrumentPreset>(ctx.style.instrumentPreset);
    
    double arpeggioRate = ctx.params.tempoBpm / 60.0;
    arpeggioRate *= (0.5 + ctx.params.energy * 1.5);
    
    int numDegrees = 5 + static_cast<int>(ctx.params.energy * 3.0);
    numDegrees = std::min(numDegrees, static_cast<int>(ctx.scale.size() + 2));
    
    double arpPosition = ctx.t * arpeggioRate;
    int currentDegree = static_cast<int>(arpPosition) % numDegrees;
    
    // Envelope shaped by instrument preset and mood
    double noteFraction = std::fmod(arpPosition, 1.0);
    double envelope = 0.0;
    
    // Pluck has faster attack/decay; pad has slower
    double attackTime = (preset == PLUCK) ? 0.05 : 0.1;
    double decayTime = (preset == PLUCK) ? 0.2 : 0.3;
    
    if (noteFraction < attackTime) {
        envelope = noteFraction / attackTime;
    } else if (noteFraction < (1.0 - decayTime)) {
        envelope = 1.0;
    } else {
        envelope = (1.0 - noteFraction) / decayTime;
    }
    
    // Low mood = shorter, drier notes
    envelope *= (0.6 + 0.4 * ctx.style.moodScore);
    
    double freq = getScaleNoteFreq(ctx.params.baseFrequency, ctx.scale, currentDegree);
    double phaseStep = 2.0 * M_PI * freq / SAMPLE_RATE;
    
    double sample = instrumentOscillator(preset, ctx.phases[0], ctx.params.brightness) * envelope;
    
    ctx.phases[0] += phaseStep;
    if (ctx.phases[0] > 2.0 * M_PI) ctx.phases[0] -= 2.0 * M_PI;
    
    return sample * 0.5;
}

static double synthChordSample(SynthContext& ctx) {
    InstrumentPreset preset = static_cast<InstrumentPreset>(ctx.style.instrumentPreset);
    
    int numNotes = 2 + static_cast<int>(ctx.params.energy * 2.0);
    numNotes = std::min(numNotes, 4);
    
    double beatsPerChord = 4.0 - ctx.params.energy * 2.0;
    beatsPerChord = std::max(beatsPerChord, 1.0);
    
    double beatPosition = ctx.t / ctx.secondsPerBeat;
    int chordIndex = static_cast<int>(beatPosition / beatsPerChord);
    
    std::vector<int> chordDegrees;
    switch (chordIndex % 3) {
        case 0: chordDegrees = {0, 2, 4, 6}; break;
        case 1: chordDegrees = {3, 5, 0, 2}; break;
        case 2: chordDegrees = {4, 6, 1, 3}; break;
    }
    
    double beatFraction = std::fmod(beatPosition, 1.0);
    double rhythmEnv = 0.0;
    
    if (beatFraction < 0.05) {
        rhythmEnv = beatFraction / 0.05;
    } else if (beatFraction < 0.8) {
        rhythmEnv = 1.0 - (beatFraction - 0.05) * 0.3;
    } else {
        rhythmEnv = 0.7 - (beatFraction - 0.8) * 2.0;
    }
    rhythmEnv = std::max(0.0, rhythmEnv);
    
    // Mood affects sustain
    rhythmEnv *= (0.5 + 0.5 * ctx.style.moodScore);
    
    double sample = 0.0;
    
    for (int i = 0; i < numNotes; ++i) {
        double freq = getScaleNoteFreq(ctx.params.baseFrequency, ctx.scale, chordDegrees[i]);
        double phaseStep = 2.0 * M_PI * freq / SAMPLE_RATE;
        
        double noteValue = instrumentOscillator(preset, ctx.phases[i], ctx.params.brightness);
        sample += noteValue * rhythmEnv / static_cast<double>(numNotes);
        
        ctx.phases[i] += phaseStep;
        if (ctx.phases[i] > 2.0 * M_PI) ctx.phases[i] -= 2.0 * M_PI;
    }
    
    return sample * 0.7;
}

// === Phase 7: Melodic line layer ===
static double synthMelodySample(SynthContext& ctx, int& currentMelodyDegree, 
                                double& timeSinceChange, std::mt19937& rng) {
    // Only play melody if energy and mood are sufficient
    if (ctx.params.energy < 0.3 || ctx.style.moodScore < 0.4) {
        return 0.0;
    }
    
    // Change melody note every 2-4 beats
    double beatsPerNote = 2.0 + (1.0 - ctx.params.energy) * 2.0;
    double secondsPerNote = beatsPerNote * ctx.secondsPerBeat;
    
    if (timeSinceChange >= secondsPerNote) {
        // Random walk through scale
        std::uniform_int_distribution<int> stepDist(-1, 1);
        int step = stepDist(rng);
        currentMelodyDegree = std::clamp(currentMelodyDegree + step, 0, 7);
        timeSinceChange = 0.0;
    }
    
    // Envelope for melody note
    double notePhase = timeSinceChange / secondsPerNote;
    double envelope = 0.0;
    
    if (notePhase < 0.1) {
        envelope = notePhase / 0.1;
    } else if (notePhase < 0.7) {
        envelope = 1.0 - (notePhase - 0.1) * 0.3;
    } else {
        envelope = 0.7 - (notePhase - 0.7) * 1.5;
    }
    envelope = std::max(0.0, envelope);
    
    // Use bell or soft keys for melody
    InstrumentPreset melodyPreset = (ctx.style.instrumentPreset == BELL) ? BELL : SOFT_KEYS;
    
    double freq = getScaleNoteFreq(ctx.params.baseFrequency * 2.0, ctx.scale, currentMelodyDegree);
    double phaseStep = 2.0 * M_PI * freq / SAMPLE_RATE;
    
    // Use last phase slot for melody
    double sample = instrumentOscillator(melodyPreset, ctx.phases[7], ctx.params.brightness) * envelope;
    
    ctx.phases[7] += phaseStep;
    if (ctx.phases[7] > 2.0 * M_PI) ctx.phases[7] -= 2.0 * M_PI;
    
    timeSinceChange += 1.0 / SAMPLE_RATE;
    
    return sample * 0.25;  // Quiet melody layer
}

}  // namespace

// === Phase 7: Main track generation with all layers ===
void generateAmbientTrack(const std::string& outputPath, 
                          const MusicParameters& params,
                          const StyleParameters& style) {
    
    std::cout << "[INFO] Generating ambient track with Phase 7 enhancements...\n";
    std::cout << "  Ambience: " << style.ambienceType << ", Instrument: " 
              << style.instrumentPreset << ", Mood: " << style.moodScore << "\n";
    
    const double durationSeconds = 8.0 + params.energy * 4.0;
    const int numSamples = static_cast<int>(durationSeconds * SAMPLE_RATE);

    std::ofstream out(outputPath, std::ios::binary);
    if (!out) {
        throw std::runtime_error("Failed to open output WAV: " + outputPath);
    }

    // Write WAV header
    int numChannels = 1;
    int bitsPerSample = 16;
    int byteRate = SAMPLE_RATE * numChannels * bitsPerSample / 8;
    int blockAlign = numChannels * bitsPerSample / 8;
    int dataSize = numSamples * numChannels * bitsPerSample / 8;
    int chunkSize = 36 + dataSize;

    out.write("RIFF", 4);
    writeLE(out, chunkSize, 4);
    out.write("WAVE", 4);

    out.write("fmt ", 4);
    writeLE(out, 16, 4);
    writeLE(out, 1, 2);
    writeLE(out, numChannels, 2);
    writeLE(out, SAMPLE_RATE, 4);
    writeLE(out, byteRate, 4);
    writeLE(out, blockAlign, 2);
    writeLE(out, bitsPerSample, 2);

    out.write("data", 4);
    writeLE(out, dataSize, 4);

    // === Musical synthesis ===
    auto scale = getScaleSemitones(params.scaleType);
    double secondsPerBeat = 60.0 / params.tempoBpm;
    
    // Reverb parameters - reduced for low mood
    int baseDelaySamples = static_cast<int>(0.25 * SAMPLE_RATE);
    float moodAdjustedReverb = params.reverb * (0.5f + 0.5f * style.moodScore);
    int delaySamples = baseDelaySamples + static_cast<int>(moodAdjustedReverb * 0.15 * SAMPLE_RATE);
    delaySamples = std::min(delaySamples, static_cast<int>(0.5 * SAMPLE_RATE));
    
    std::vector<float> delayBuffer(delaySamples, 0.0f);
    int delayIndex = 0;
    double reverbFeedback = 0.2 + moodAdjustedReverb * 0.4;
    
    std::vector<double> phases(8, 0.0);
    
    float filterState = 0.0f;
    double filterCoeff = 0.7 + params.brightness * 0.25;
    
    // Melody state
    int currentMelodyDegree = 0;
    double timeSinceChange = 0.0;
    std::mt19937 rng(42);
    
    // Ambience gain based on mood
    float ambienceGain = 0.15f + 0.35f * style.moodScore;
    
    double t = 0.0;
    double dt = 1.0 / SAMPLE_RATE;
    
    for (int i = 0; i < numSamples; ++i) {
        SynthContext ctx = {t, params, style, scale, secondsPerBeat, phases};
        
        // === Layer 1: Main musical pattern ===
        double musical = 0.0;
        
        if (params.patternType == 0) {
            musical = synthPadSample(ctx);
        } else if (params.patternType == 1) {
            musical = synthArpSample(ctx);
        } else {
            musical = synthChordSample(ctx);
        }
        
        // === Layer 2: Melodic line (optional) ===
        double melody = synthMelodySample(ctx, currentMelodyDegree, timeSinceChange, rng);
        
        // Combine musical layers
        double dry = musical + melody;
        
        // Filter
        filterState = filterState * (1.0 - filterCoeff) + dry * filterCoeff;
        double filtered = filterState;
        
        // Reverb
        float delayed = delayBuffer[delayIndex];
        float reverbSignal = filtered + delayed * reverbFeedback;
        delayBuffer[delayIndex] = reverbSignal;
        delayIndex = (delayIndex + 1) % delaySamples;
        
        double dryMix = 1.0 - moodAdjustedReverb * 0.6;
        double wetMix = moodAdjustedReverb * 0.8;
        float musicalLayer = filtered * dryMix + reverbSignal * wetMix;
        
        // === Layer 3: Ambience ===
        float ambienceSample = getAmbienceSample(style.ambienceType, i);
        
        // Simple high-pass filter on ambience to prevent muddiness
        static float ambFilterState = 0.0f;
        float ambFiltered = ambienceSample - ambFilterState;
        ambFilterState = ambFilterState * 0.95f + ambienceSample * 0.05f;
        
        // === Mix all layers ===
        float combined = musicalLayer + ambienceGain * ambFiltered;
        
        // Global envelope
        double globalEnv = 1.0;
        if (i < SAMPLE_RATE * 0.5) {
            globalEnv = static_cast<double>(i) / (SAMPLE_RATE * 0.5);
        } else if (i > numSamples - SAMPLE_RATE * 1.0) {
            globalEnv = static_cast<double>(numSamples - i) / (SAMPLE_RATE * 1.0);
        }
        
        float sample = combined * globalEnv;
        
        // Soft clipping
        if (sample > 0.9f) {
            sample = 0.9f + 0.1f * std::tanh((sample - 0.9f) / 0.1f);
        } else if (sample < -0.9f) {
            sample = -0.9f + 0.1f * std::tanh((sample + 0.9f) / 0.1f);
        }
        
        sample = std::max(-1.0f, std::min(1.0f, sample));
        
        int16_t intSample = static_cast<int16_t>(sample * 32767.0f);
        writeLE(out, static_cast<std::uint16_t>(intSample), 2);
        
        t += dt;
    }

    out.close();
    if (!out) {
        throw std::runtime_error("Error while writing WAV file: " + outputPath);
    }
    
    std::cout << "[INFO] Track generated successfully: " << outputPath << "\n";
}
