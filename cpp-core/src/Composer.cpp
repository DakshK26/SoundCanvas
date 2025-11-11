#include "Composer.hpp"
#include "MidiWriter.hpp"
#include "SongSpec.hpp"
#include "SectionPlanner.hpp"
#include "GenreTemplate.hpp"
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <map>
#include <iostream>

namespace {

// Musical scale intervals in semitones
std::vector<int> getScaleIntervals(int scaleType) {
    switch (scaleType) {
        case 0: // Major
            return {0, 2, 4, 5, 7, 9, 11};
        case 1: // Minor
            return {0, 2, 3, 5, 7, 8, 10};
        case 2: // Dorian
            return {0, 2, 3, 5, 7, 9, 10};
        case 3: // Lydian
            return {0, 2, 4, 6, 7, 9, 11};
        default:
            return {0, 2, 4, 5, 7, 9, 11};
    }
}

// Chord progression templates for different scale types
struct ChordProgression {
    std::vector<int> degrees; // Scale degrees (0-6)
    std::string name;
};

std::vector<ChordProgression> getProgressions(int scaleType) {
    if (scaleType == 0 || scaleType == 3) {
        // Major / Lydian progressions
        return {
            {{0, 5, 3, 4}, "I-vi-IV-V"},
            {{0, 4, 0, 5}, "I-V-I-vi"},
            {{0, 3, 4, 4}, "I-IV-V-V"}
        };
    } else {
        // Minor / Dorian progressions
        return {
            {{0, 3, 5, 5}, "i-iv-VI-VI"},
            {{0, 4, 3, 5}, "i-v-iv-VI"},
            {{0, 5, 3, 3}, "i-VI-iv-iv"}
        };
    }
}

// Random number generator for humanization
std::mt19937& getRng() {
    static std::mt19937 rng(42); // Fixed seed for reproducibility
    return rng;
}

float randomFloat(float min, float max) {
    std::uniform_real_distribution<float> dist(min, max);
    return dist(getRng());
}

int randomInt(int min, int max) {
    std::uniform_int_distribution<int> dist(min, max);
    return dist(getRng());
}

// Generate drums for one bar
void generateDrumsBar(MidiWriter& midi, int trackIdx, int startTick, int ticksPerBar,
                      GrooveType groove, float energy, float complexity) {
    int ticksPerBeat = ticksPerBar / 4;
    int channel = 9; // MIDI channel 10 (9 in 0-indexed) = drums
    
    // General MIDI drum map
    const int kick = 36;
    const int snare = 38;
    const int closedHat = 42;
    const int openHat = 46;
    
    int baseVelocity = 80 + static_cast<int>(energy * 30);
    
    if (groove == GrooveType::CHILL) {
        // Sparse, laid-back pattern
        // Kick on 1 and 3
        midi.addNoteOn(trackIdx, startTick, channel, kick, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat/2, channel, kick);
        
        midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, kick, baseVelocity - 10);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 + ticksPerBeat/2, channel, kick);
        
        // Sparse hi-hats
        if (complexity > 0.3f) {
            for (int beat = 0; beat < 4; ++beat) {
                int vel = baseVelocity - 20 + randomInt(-5, 5);
                midi.addNoteOn(trackIdx, startTick + beat * ticksPerBeat, channel, closedHat, vel);
                midi.addNoteOff(trackIdx, startTick + beat * ticksPerBeat + ticksPerBeat/4, channel, closedHat);
            }
        }
        
    } else if (groove == GrooveType::DRIVING) {
        // Energetic 4-on-floor pattern
        // Kick on every beat
        for (int beat = 0; beat < 4; ++beat) {
            int vel = baseVelocity + randomInt(-5, 5);
            midi.addNoteOn(trackIdx, startTick + beat * ticksPerBeat, channel, kick, vel);
            midi.addNoteOff(trackIdx, startTick + beat * ticksPerBeat + ticksPerBeat/2, channel, kick);
        }
        
        // Snare on 2 and 4
        midi.addNoteOn(trackIdx, startTick + ticksPerBeat, channel, snare, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat + ticksPerBeat/2, channel, snare);
        
        midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 3, channel, snare, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 3 + ticksPerBeat/2, channel, snare);
        
        // 8th note hi-hats
        for (int i = 0; i < 8; ++i) {
            int vel = baseVelocity - 10 + randomInt(-5, 5);
            int hat = (i % 4 == 3 && complexity > 0.6f) ? openHat : closedHat;
            midi.addNoteOn(trackIdx, startTick + i * (ticksPerBeat/2), channel, hat, vel);
            midi.addNoteOff(trackIdx, startTick + i * (ticksPerBeat/2) + ticksPerBeat/4, channel, hat);
        }
        
    } else {
        // STRAIGHT: Standard rock/pop beat
        // Kick on 1 and 3
        midi.addNoteOn(trackIdx, startTick, channel, kick, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat/2, channel, kick);
        
        midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, kick, baseVelocity - 5);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 + ticksPerBeat/2, channel, kick);
        
        // Snare on 2 and 4
        midi.addNoteOn(trackIdx, startTick + ticksPerBeat, channel, snare, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat + ticksPerBeat/2, channel, snare);
        
        midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 3, channel, snare, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 3 + ticksPerBeat/2, channel, snare);
        
        // Quarter note hi-hats
        for (int beat = 0; beat < 4; ++beat) {
            int vel = baseVelocity - 15 + randomInt(-5, 5);
            midi.addNoteOn(trackIdx, startTick + beat * ticksPerBeat, channel, closedHat, vel);
            midi.addNoteOff(trackIdx, startTick + beat * ticksPerBeat + ticksPerBeat/4, channel, closedHat);
        }
    }
}

// Generate bass line for one bar
void generateBassBar(MidiWriter& midi, int trackIdx, int startTick, int ticksPerBar,
                     int rootNote, int chordDegree, const std::vector<int>& scale,
                     int channel, float energy, float complexity) {
    int ticksPerBeat = ticksPerBar / 4;
    int baseVelocity = 70 + static_cast<int>(energy * 20);
    
    // Bass plays root of current chord, octave down
    int bassNote = rootNote - 12 + scale[chordDegree % scale.size()];
    
    if (complexity < 0.3f) {
        // Simple: whole notes
        midi.addNoteOn(trackIdx, startTick, channel, bassNote, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, bassNote);
    } else if (complexity < 0.6f) {
        // Medium: root on 1 and 3
        midi.addNoteOn(trackIdx, startTick, channel, bassNote, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 - 10, channel, bassNote);
        
        midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, bassNote, baseVelocity - 5);
        midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, bassNote);
    } else {
        // Walking bass: root + fifth pattern
        int fifthNote = rootNote - 12 + scale[(chordDegree + 4) % scale.size()];
        
        midi.addNoteOn(trackIdx, startTick, channel, bassNote, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat - 10, channel, bassNote);
        
        midi.addNoteOn(trackIdx, startTick + ticksPerBeat, channel, fifthNote, baseVelocity - 10);
        midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 - 10, channel, fifthNote);
        
        midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, bassNote, baseVelocity - 5);
        midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, bassNote);
    }
}

// Generate chord voicing for one bar
void generateChordBar(MidiWriter& midi, int trackIdx, int startTick, int ticksPerBar,
                      int rootNote, int chordDegree, const std::vector<int>& scale,
                      int channel, float energy, float complexity) {
    int ticksPerBeat = ticksPerBar / 4;
    int baseVelocity = 60 + static_cast<int>(energy * 15);
    
    // Build triad: root, third, fifth
    std::vector<int> chordNotes;
    chordNotes.push_back(rootNote + scale[chordDegree % scale.size()]);
    chordNotes.push_back(rootNote + scale[(chordDegree + 2) % scale.size()]);
    chordNotes.push_back(rootNote + scale[(chordDegree + 4) % scale.size()]);
    
    if (complexity < 0.4f) {
        // Whole note chords
        for (int note : chordNotes) {
            midi.addNoteOn(trackIdx, startTick, channel, note, baseVelocity);
            midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, note);
        }
    } else {
        // Rhythmic chords on beats 1 and 3
        for (int note : chordNotes) {
            midi.addNoteOn(trackIdx, startTick, channel, note, baseVelocity);
            midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 - 10, channel, note);
            
            midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, note, baseVelocity - 5);
            midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, note);
        }
    }
}

// Generate melody for one bar
void generateMelodyBar(MidiWriter& midi, int trackIdx, int startTick, int ticksPerBar,
                       int rootNote, int chordDegree, const std::vector<int>& scale,
                       int channel, float moodScore, int& melodicState) {
    int ticksPerBeat = ticksPerBar / 4;
    int baseVelocity = 70 + static_cast<int>(moodScore * 20);
    
    // Simple melodic motif based on current chord
    // Use stepwise motion within the scale
    int noteCount = (moodScore > 0.6f) ? 4 : 2;
    
    for (int i = 0; i < noteCount; ++i) {
        // Random walk through scale degrees
        int degree = (chordDegree + melodicState) % scale.size();
        melodicState += randomInt(-1, 2); // Step up/down/stay
        melodicState = std::max(0, std::min(6, melodicState));
        
        int note = rootNote + 12 + scale[degree]; // Octave up from root
        int tick = startTick + i * (ticksPerBar / noteCount);
        int duration = (ticksPerBar / noteCount) - 10;
        
        int velocity = baseVelocity + randomInt(-10, 10);
        midi.addNoteOn(trackIdx, tick, channel, note, velocity);
        midi.addNoteOff(trackIdx, tick + duration, channel, note);
    }
}

// Generate pad (sustained chords) for one bar
void generatePadBar(MidiWriter& midi, int trackIdx, int startTick, int ticksPerBar,
                    int rootNote, int chordDegree, const std::vector<int>& scale,
                    int channel, float moodScore) {
    int baseVelocity = 50 + static_cast<int>(moodScore * 15);
    
    // Pad plays simple sustained chords (root + third or root + fifth)
    std::vector<int> padNotes;
    padNotes.push_back(rootNote + scale[chordDegree % scale.size()]);
    
    if (moodScore > 0.5f) {
        // Add third for more lush sound
        padNotes.push_back(rootNote + scale[(chordDegree + 2) % scale.size()]);
    }
    
    for (int note : padNotes) {
        midi.addNoteOn(trackIdx, startTick, channel, note, baseVelocity);
        midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, note);
    }
}

} // anonymous namespace

void composeSongToMidi(const SongSpec& spec, const std::string& midiPath) {
    MidiWriter midi(480); // 480 ticks per quarter note
    midi.setTempo(spec.tempoBpm);
    midi.setTimeSignature(4, 4);
    
    // Calculate timing
    int ticksPerQuarter = 480;
    int ticksPerBar = ticksPerQuarter * 4; // 4/4 time
    
    // Get scale intervals
    std::vector<int> scale = getScaleIntervals(spec.scaleType);
    
    // Get chord progression
    auto progressions = getProgressions(spec.scaleType);
    auto progression = progressions[0]; // Use first progression (can be randomized)
    
    // Create tracks
    std::map<std::string, int> trackIndices;
    std::map<std::string, int> channelMap;
    int nextChannel = 0;
    
    for (const auto& trackSpec : spec.tracks) {
        int trackIdx = midi.addTrack(trackSpec.role);
        trackIndices[trackSpec.role] = trackIdx;
        
        if (trackSpec.role == "drums") {
            channelMap[trackSpec.role] = 9; // MIDI channel 10 (drums)
        } else {
            channelMap[trackSpec.role] = nextChannel++;
            if (nextChannel == 9) nextChannel++; // Skip drum channel
            
            // Add program change at start
            midi.addProgramChange(trackIdx, 0, channelMap[trackSpec.role], trackSpec.midiProgram);
        }
    }
    
    // Compose each section
    int currentTick = 0;
    int melodicState = 2; // Start on third degree for melody
    
    for (const auto& section : spec.sections) {
        float sectionEnergy = section.energy;
        
        // Generate bars for this section
        for (int bar = 0; bar < section.bars; ++bar) {
            // Current chord from progression
            int progressionIndex = bar % progression.degrees.size();
            int chordDegree = progression.degrees[progressionIndex];
            
            // Generate each track for this bar
            for (const auto& trackSpec : spec.tracks) {
                int trackIdx = trackIndices[trackSpec.role];
                int channel = channelMap[trackSpec.role];
                
                if (trackSpec.role == "drums") {
                    generateDrumsBar(midi, trackIdx, currentTick, ticksPerBar,
                                   spec.groove, sectionEnergy, trackSpec.complexity);
                } else if (trackSpec.role == "bass") {
                    generateBassBar(midi, trackIdx, currentTick, ticksPerBar,
                                  spec.rootMidiNote, chordDegree, scale,
                                  channel, sectionEnergy, trackSpec.complexity);
                } else if (trackSpec.role == "chords") {
                    generateChordBar(midi, trackIdx, currentTick, ticksPerBar,
                                   spec.rootMidiNote, chordDegree, scale,
                                   channel, sectionEnergy, trackSpec.complexity);
                } else if (trackSpec.role == "melody") {
                    generateMelodyBar(midi, trackIdx, currentTick, ticksPerBar,
                                    spec.rootMidiNote, chordDegree, scale,
                                    channel, spec.moodScore, melodicState);
                } else if (trackSpec.role == "pad") {
                    generatePadBar(midi, trackIdx, currentTick, ticksPerBar,
                                 spec.rootMidiNote, chordDegree, scale,
                                 channel, spec.moodScore);
                }
            }
            
            currentTick += ticksPerBar;
        }
    }
    
    // Write MIDI file
    midi.write(midiPath);
}

// ============================================================================
// PHASE 8: GENRE-AWARE COMPOSITION
// ============================================================================

void composeGenreSongToMidi(const SongPlan& plan, const std::string& midiPath) {
    // For now, convert SongPlan to SongSpec and use existing composer
    // TODO: Later implement full pattern-based composition with automation
    SongSpec spec = songPlanToSpec(plan);
    
    // Add genre information to output
    std::cout << "[Genre Composition] " << genreTypeName(plan.genre) << std::endl;
    std::cout << "[Sections] ";
    for (const auto& sec : plan.sections) {
        std::cout << sectionTypeName(sec.type);
        if (sec.hasDrop) std::cout << "*";
        std::cout << "(" << sec.bars << ") ";
    }
    std::cout << std::endl;
    
    // Use the existing composition engine
    composeSongToMidi(spec, midiPath);
}

