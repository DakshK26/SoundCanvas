#include "AudioEngine.hpp"
#include <cmath>
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <vector>
#include <algorithm>

namespace {

constexpr int SAMPLE_RATE = 44100;

// Write little-endian helper
void writeLE(std::ofstream& out, std::uint32_t value, int bytes) {
    for (int i = 0; i < bytes; ++i) {
        out.put(static_cast<char>(value & 0xFF));
        value >>= 8;
    }
}

// Musical scale intervals in semitones
static std::vector<int> getScaleSemitones(int scaleType) {
    // Intervals from root in semitones
    switch (scaleType) {
        case 0: // Major - bright, happy
            return {0, 2, 4, 5, 7, 9, 11};
        case 1: // Minor - dark, sad
            return {0, 2, 3, 5, 7, 8, 10};
        case 2: // Dorian - jazzy, modal
            return {0, 2, 3, 5, 7, 9, 10};
        case 3: // Lydian - dreamy, ethereal
        default:
            return {0, 2, 4, 6, 7, 9, 11};
    }
}

// MIDI conversion helpers
static double baseFreqToMidi(double freq) {
    return 69.0 + 12.0 * std::log2(freq / 440.0);
}

static double midiToFreq(double midi) {
    return 440.0 * std::pow(2.0, (midi - 69.0) / 12.0);
}

// Get frequency for a scale degree above the root
static double getScaleNoteFreq(double baseFreq, const std::vector<int>& scale, int degree) {
    double baseMidi = baseFreqToMidi(baseFreq);
    int semitones = scale[degree % scale.size()];
    int octaves = degree / static_cast<int>(scale.size());
    double noteMidi = baseMidi + semitones + (octaves * 12);
    return midiToFreq(noteMidi);
}

// Simple oscillator with multiple waveforms blended by brightness
static double oscillator(double phase, double brightness) {
    // brightness = 0 → pure sine (dark, mellow)
    // brightness = 1 → mix with triangle/saw (bright, rich harmonics)
    
    double sine = std::sin(phase);
    
    // Triangle wave (approximation)
    double triangle = std::asin(std::sin(phase)) * (2.0 / M_PI);
    
    // Blend based on brightness
    return sine * (1.0 - brightness * 0.4) + triangle * (brightness * 0.4);
}

// Context structure for pattern synthesis
struct SynthContext {
    double t;                           // Current time in seconds
    const MusicParameters& params;
    const std::vector<int>& scale;
    double secondsPerBeat;
    std::vector<double>& phases;        // Oscillator phases (persistent)
};

// Pattern 0: Pad - sustained drone with 1-3 chord tones, slow LFO
static double synthPadSample(SynthContext& ctx) {
    // Energy controls number of notes (0 = 1 note, 1 = 3 notes)
    int numNotes = 1 + static_cast<int>(ctx.params.energy * 2.0);
    numNotes = std::min(numNotes, 3);
    
    // Very slow LFO for gentle amplitude modulation (based on tempo)
    double lfoFreq = ctx.params.tempoBpm / 240.0;  // ~0.2-0.4 Hz
    double lfo = 0.8 + 0.2 * std::sin(2.0 * M_PI * lfoFreq * ctx.t);
    
    double sample = 0.0;
    
    // Play root, third, fifth (or subset based on energy)
    std::vector<int> degrees = {0, 2, 4};  // Scale degrees for triad
    
    for (int i = 0; i < numNotes; ++i) {
        double freq = getScaleNoteFreq(ctx.params.baseFrequency, ctx.scale, degrees[i]);
        double phaseStep = 2.0 * M_PI * freq / SAMPLE_RATE;
        
        double noteValue = oscillator(ctx.phases[i], ctx.params.brightness);
        sample += noteValue * lfo / static_cast<double>(numNotes);
        
        ctx.phases[i] += phaseStep;
        if (ctx.phases[i] > 2.0 * M_PI) ctx.phases[i] -= 2.0 * M_PI;
    }
    
    return sample * 0.6;  // Pad is gentle
}

// Pattern 1: Arpeggio - step through scale notes rhythmically
static double synthArpSample(SynthContext& ctx) {
    // Energy controls arp speed multiplier and range
    double arpeggioRate = ctx.params.tempoBpm / 60.0;  // Base: 1 note per beat
    arpeggioRate *= (0.5 + ctx.params.energy * 1.5);   // Energy: 0.5x to 2x speed
    
    // Determine which scale degree to play based on time
    int numDegrees = 5 + static_cast<int>(ctx.params.energy * 3.0);  // 5-8 notes
    numDegrees = std::min(numDegrees, static_cast<int>(ctx.scale.size() + 2));
    
    double arpPosition = ctx.t * arpeggioRate;
    int currentDegree = static_cast<int>(arpPosition) % numDegrees;
    
    // Envelope for each note (attack/decay)
    double noteFraction = std::fmod(arpPosition, 1.0);
    double envelope = 0.0;
    if (noteFraction < 0.1) {
        envelope = noteFraction / 0.1;  // Attack
    } else if (noteFraction < 0.7) {
        envelope = 1.0;  // Sustain
    } else {
        envelope = (1.0 - noteFraction) / 0.3;  // Decay
    }
    
    double freq = getScaleNoteFreq(ctx.params.baseFrequency, ctx.scale, currentDegree);
    double phaseStep = 2.0 * M_PI * freq / SAMPLE_RATE;
    
    double sample = oscillator(ctx.phases[0], ctx.params.brightness) * envelope;
    
    ctx.phases[0] += phaseStep;
    if (ctx.phases[0] > 2.0 * M_PI) ctx.phases[0] -= 2.0 * M_PI;
    
    return sample * 0.5;  // Arp is crisp
}

// Pattern 2: Chords - block chords with rhythmic changes
static double synthChordSample(SynthContext& ctx) {
    // Energy controls chord complexity and change rate
    int numNotes = 2 + static_cast<int>(ctx.params.energy * 2.0);  // 2-4 notes
    numNotes = std::min(numNotes, 4);
    
    // Change chord every N beats
    double beatsPerChord = 4.0 - ctx.params.energy * 2.0;  // 2-4 beats
    beatsPerChord = std::max(beatsPerChord, 1.0);
    
    double beatPosition = ctx.t / ctx.secondsPerBeat;
    int chordIndex = static_cast<int>(beatPosition / beatsPerChord);
    
    // Use different chord inversions/voicings based on chordIndex
    std::vector<int> chordDegrees;
    switch (chordIndex % 3) {
        case 0: chordDegrees = {0, 2, 4, 6}; break;  // I chord
        case 1: chordDegrees = {3, 5, 0, 2}; break;  // IV chord
        case 2: chordDegrees = {4, 6, 1, 3}; break;  // V chord
    }
    
    // Rhythmic envelope (pulsing on beats)
    double beatFraction = std::fmod(beatPosition, 1.0);
    double rhythmEnv = 0.0;
    if (beatFraction < 0.05) {
        rhythmEnv = beatFraction / 0.05;  // Attack
    } else if (beatFraction < 0.8) {
        rhythmEnv = 1.0 - (beatFraction - 0.05) * 0.3;  // Gentle decay
    } else {
        rhythmEnv = 0.7 - (beatFraction - 0.8) * 2.0;  // Release
    }
    rhythmEnv = std::max(0.0, rhythmEnv);
    
    double sample = 0.0;
    
    for (int i = 0; i < numNotes; ++i) {
        double freq = getScaleNoteFreq(ctx.params.baseFrequency, ctx.scale, chordDegrees[i]);
        double phaseStep = 2.0 * M_PI * freq / SAMPLE_RATE;
        
        double noteValue = oscillator(ctx.phases[i], ctx.params.brightness);
        sample += noteValue * rhythmEnv / static_cast<double>(numNotes);
        
        ctx.phases[i] += phaseStep;
        if (ctx.phases[i] > 2.0 * M_PI) ctx.phases[i] -= 2.0 * M_PI;
    }
    
    return sample * 0.7;  // Chords are rich and full
}

}  // namespace

void generateAmbientTrack(const std::string& outputPath, const MusicParameters& params) {
    // Duration based on energy (more energy = slightly longer, more complex)
    const double durationSeconds = 8.0 + params.energy * 4.0;  // 8-12 seconds
    const int numSamples = static_cast<int>(durationSeconds * SAMPLE_RATE);

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

    // --- Musical synthesis with 7 parameters ---
    
    auto scale = getScaleSemitones(params.scaleType);
    double secondsPerBeat = 60.0 / params.tempoBpm;
    
    // Reverb: simple feedback delay line
    // Reverb amount controls delay time and feedback
    int baseDelaySamples = static_cast<int>(0.25 * SAMPLE_RATE);  // 250ms base
    int delaySamples = baseDelaySamples + static_cast<int>(params.reverb * 0.15 * SAMPLE_RATE);
    delaySamples = std::min(delaySamples, static_cast<int>(0.5 * SAMPLE_RATE));  // Max 500ms
    
    std::vector<float> delayBuffer(delaySamples, 0.0f);
    int delayIndex = 0;
    double reverbFeedback = 0.3 + params.reverb * 0.4;  // 0.3-0.7 feedback
    
    // Oscillator phases (persistent across samples)
    std::vector<double> phases(8, 0.0);  // Support up to 8 voices
    
    // Low-pass filter state for brightness control
    float filterState = 0.0f;
    double filterCoeff = 0.7 + params.brightness * 0.25;  // 0.7-0.95 (higher = brighter)
    
    double t = 0.0;
    double dt = 1.0 / SAMPLE_RATE;
    
    for (int i = 0; i < numSamples; ++i) {
        // Build synthesis context
        SynthContext ctx = {t, params, scale, secondsPerBeat, phases};
        
        // Generate dry signal based on pattern type
        double dry = 0.0;
        
        if (params.patternType == 0) {
            // Pad: sustained, ambient
            dry = synthPadSample(ctx);
        } else if (params.patternType == 1) {
            // Arpeggio: rhythmic, flowing
            dry = synthArpSample(ctx);
        } else {
            // Chords: harmonic blocks
            dry = synthChordSample(ctx);
        }
        
        // Simple one-pole low-pass filter controlled by brightness
        // Higher brightness = less filtering = brighter sound
        filterState = filterState * (1.0 - filterCoeff) + dry * filterCoeff;
        double filtered = filterState;
        
        // Reverb processing
        float delayed = delayBuffer[delayIndex];
        float reverbSignal = filtered + delayed * reverbFeedback;
        
        delayBuffer[delayIndex] = reverbSignal;
        delayIndex = (delayIndex + 1) % delaySamples;
        
        // Mix dry and wet based on reverb amount
        double dryMix = 1.0 - params.reverb * 0.6;  // Always keep some dry
        double wetMix = params.reverb * 0.8;
        float mixed = filtered * dryMix + reverbSignal * wetMix;
        
        // Global envelope (fade in/out for smooth start/end)
        double globalEnv = 1.0;
        if (i < SAMPLE_RATE * 0.5) {
            // Fade in over 0.5 seconds
            globalEnv = static_cast<double>(i) / (SAMPLE_RATE * 0.5);
        } else if (i > numSamples - SAMPLE_RATE * 1.0) {
            // Fade out over 1 second
            globalEnv = static_cast<double>(numSamples - i) / (SAMPLE_RATE * 1.0);
        }
        
        float sample = mixed * globalEnv;
        
        // Soft clipping to prevent harsh distortion
        if (sample > 0.9f) {
            sample = 0.9f + 0.1f * std::tanh((sample - 0.9f) / 0.1f);
        } else if (sample < -0.9f) {
            sample = -0.9f + 0.1f * std::tanh((sample + 0.9f) / 0.1f);
        }
        
        // Final hard limit
        sample = std::max(-1.0f, std::min(1.0f, sample));
        
        // Convert to 16-bit PCM
        int16_t intSample = static_cast<int16_t>(sample * 32767.0f);
        writeLE(out, static_cast<std::uint16_t>(intSample), 2);
        
        t += dt;
    }

    out.close();
    if (!out) {
        throw std::runtime_error("Error while writing WAV file: " + outputPath);
    }
}