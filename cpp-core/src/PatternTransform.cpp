#include "PatternTransform.hpp"
#include <algorithm>
#include <cmath>
#include <random>

// ============================================================================
// PATTERN TRANSFORMATION FUNCTIONS
// ============================================================================

void transposePattern(MidiPattern& pattern, int semitones) {
    for (auto& note : pattern.notes) {
        note.note = std::clamp(note.note + semitones, 0, 127);
    }
}

void scaleVelocity(MidiPattern& pattern, float factor) {
    for (auto& note : pattern.notes) {
        int newVel = static_cast<int>(note.velocity * factor);
        note.velocity = std::clamp(newVel, 1, 127);
    }
}

void thinNotes(MidiPattern& pattern, float keepRatio) {
    if (keepRatio >= 1.0f) return;
    if (keepRatio <= 0.0f) {
        pattern.notes.clear();
        return;
    }
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> dis(0.0, 1.0);
    
    // Remove notes randomly based on keepRatio
    pattern.notes.erase(
        std::remove_if(pattern.notes.begin(), pattern.notes.end(),
            [&](const MidiNote&) { return dis(gen) > keepRatio; }),
        pattern.notes.end()
    );
}

void humanize(MidiPattern& pattern, int timingVariance, int velocityVariance) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> timeDist(-timingVariance, timingVariance);
    std::uniform_int_distribution<> velDist(-velocityVariance, velocityVariance);
    
    for (auto& note : pattern.notes) {
        // Randomize timing slightly
        note.startTick = std::max(0, note.startTick + timeDist(gen));
        
        // Randomize velocity
        note.velocity = std::clamp(note.velocity + velDist(gen), 1, 127);
    }
}

std::vector<int> generateFilterSweep(int bars, float startCutoff, float endCutoff) {
    std::vector<int> sweep;
    for (int i = 0; i < bars; ++i) {
        float t = static_cast<float>(i) / (bars - 1);
        float cutoff = startCutoff + (endCutoff - startCutoff) * t;
        sweep.push_back(static_cast<int>(cutoff));
    }
    return sweep;
}

std::vector<float> generateVolumeRamp(int bars, float startVol, float endVol) {
    std::vector<float> ramp;
    for (int i = 0; i < bars; ++i) {
        float t = static_cast<float>(i) / (bars - 1);
        ramp.push_back(startVol + (endVol - startVol) * t);
    }
    return ramp;
}

// ============================================================================
// PATTERN GENERATORS (Simple procedural patterns for now)
// ============================================================================

MidiPattern createKickPattern(int bars, int beatsPerBar) {
    MidiPattern pattern;
    pattern.lengthInBars = bars;
    
    const int ticksPerBeat = 480;  // Standard MIDI resolution
    pattern.lengthInTicks = bars * beatsPerBar * ticksPerBeat;
    
    // 4-on-the-floor: kick on every beat
    for (int bar = 0; bar < bars; ++bar) {
        for (int beat = 0; beat < beatsPerBar; ++beat) {
            MidiNote note;
            note.note = 36;  // Kick drum (GM)
            note.velocity = 100;
            note.startTick = (bar * beatsPerBar + beat) * ticksPerBeat;
            note.duration = ticksPerBeat / 4;  // Short kick
            note.channel = 9;  // Drum channel
            pattern.notes.push_back(note);
        }
    }
    
    return pattern;
}

MidiPattern createHiHatPattern(int bars, bool sixteenths) {
    MidiPattern pattern;
    pattern.lengthInBars = bars;
    
    const int ticksPerBeat = 480;
    const int beatsPerBar = 4;
    pattern.lengthInTicks = bars * beatsPerBar * ticksPerBeat;
    
    int subdivision = sixteenths ? 4 : 2;  // 16th notes or 8th notes
    int ticksPerNote = ticksPerBeat / subdivision;
    
    for (int bar = 0; bar < bars; ++bar) {
        for (int beat = 0; beat < beatsPerBar; ++beat) {
            for (int sub = 0; sub < subdivision; ++sub) {
                MidiNote note;
                note.note = (sub % 2 == 0) ? 42 : 46;  // Closed/open hi-hat
                note.velocity = (sub == 0) ? 80 : 60;   // Accent on beat
                note.startTick = (bar * beatsPerBar + beat) * ticksPerBeat + sub * ticksPerNote;
                note.duration = ticksPerNote / 2;
                note.channel = 9;  // Drum channel
                pattern.notes.push_back(note);
            }
        }
    }
    
    return pattern;
}

MidiPattern createSnarePattern(int bars) {
    MidiPattern pattern;
    pattern.lengthInBars = bars;
    
    const int ticksPerBeat = 480;
    const int beatsPerBar = 4;
    pattern.lengthInTicks = bars * beatsPerBar * ticksPerBeat;
    
    // Snare on beats 2 and 4 (backbeat)
    for (int bar = 0; bar < bars; ++bar) {
        for (int beat : {1, 3}) {  // Beats 2 and 4 (0-indexed)
            MidiNote note;
            note.note = 38;  // Snare drum (GM)
            note.velocity = 100;
            note.startTick = (bar * beatsPerBar + beat) * ticksPerBeat;
            note.duration = ticksPerBeat / 4;
            note.channel = 9;  // Drum channel
            pattern.notes.push_back(note);
        }
    }
    
    return pattern;
}

MidiPattern createBassPattern(int bars, int rootNote, int scaleType, float complexity) {
    MidiPattern pattern;
    pattern.lengthInBars = bars;
    
    const int ticksPerBeat = 480;
    const int beatsPerBar = 4;
    pattern.lengthInTicks = bars * beatsPerBar * ticksPerBeat;
    
    // Define scale intervals (semitones from root)
    std::vector<int> scaleNotes;
    switch (scaleType) {
        case 0:  // Major
            scaleNotes = {0, 2, 4, 5, 7, 9, 11};
            break;
        case 1:  // Minor
            scaleNotes = {0, 2, 3, 5, 7, 8, 10};
            break;
        case 2:  // Dorian
            scaleNotes = {0, 2, 3, 5, 7, 9, 10};
            break;
        case 3:  // Lydian
            scaleNotes = {0, 2, 4, 6, 7, 9, 11};
            break;
        default:
            scaleNotes = {0, 2, 4, 5, 7, 9, 11};
    }
    
    // Simple bass pattern: root on 1, fifth on 3 (or more complex if complexity high)
    for (int bar = 0; bar < bars; ++bar) {
        // Root on beat 1
        MidiNote rootNote_;
        rootNote_.note = rootNote - 12;  // Bass octave
        rootNote_.velocity = 90;
        rootNote_.startTick = bar * beatsPerBar * ticksPerBeat;
        rootNote_.duration = ticksPerBeat * 2;
        rootNote_.channel = 0;  // Bass channel
        pattern.notes.push_back(rootNote_);
        
        if (complexity > 0.5f) {
            // Add fifth on beat 3
            MidiNote fifth;
            fifth.note = rootNote - 12 + scaleNotes[4];  // Fifth degree
            fifth.velocity = 80;
            fifth.startTick = bar * beatsPerBar * ticksPerBeat + 2 * ticksPerBeat;
            fifth.duration = ticksPerBeat;
            fifth.channel = 0;
            pattern.notes.push_back(fifth);
        }
        
        if (complexity > 0.7f) {
            // Add some eighth note movement
            for (int beat = 1; beat < 4; ++beat) {
                MidiNote fill;
                fill.note = rootNote - 12 + scaleNotes[beat % scaleNotes.size()];
                fill.velocity = 70;
                fill.startTick = bar * beatsPerBar * ticksPerBeat + beat * ticksPerBeat + ticksPerBeat / 2;
                fill.duration = ticksPerBeat / 2;
                fill.channel = 0;
                pattern.notes.push_back(fill);
            }
        }
    }
    
    return pattern;
}
