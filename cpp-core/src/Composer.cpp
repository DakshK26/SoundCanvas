#include "Composer.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <map>
#include <random>
#include <vector>

#include "GenreTemplate.hpp"
#include "MidiWriter.hpp"
#include "SectionPlanner.hpp"
#include "SongSpec.hpp"

namespace {

// Phase 9: Drum pattern data structures
struct DrumHit {
  int step;        // Position in 16th notes (0-15 for one bar in 4/4)
  int note;        // MIDI drum note number
  int velocity;    // Base velocity
};

struct DrumPattern {
  std::string name;
  std::vector<DrumHit> hits;
};

// Phase 9: Swing timing helper
// Returns adjusted tick position for swing feel
int applySwing(int tick, int ticksPerBeat, bool useSwing, float swingAmount) {
  if (!useSwing || swingAmount <= 0.0f) {
    return tick;
  }
  
  // Check if this is an off-beat (8th note subdivision)
  int ticksPerEighth = ticksPerBeat / 2;
  int positionInEighth = tick % ticksPerEighth;
  int eighthBeatIndex = (tick / ticksPerEighth) % 2;
  
  // Apply swing to off-beats (odd 8th notes: the "and" of each beat)
  if (eighthBeatIndex == 1 && positionInEighth == 0) {
    // Delay the off-beat by swingAmount
    int swingDelay = static_cast<int>(ticksPerEighth * swingAmount);
    return tick + swingDelay;
  }
  
  return tick;
}

// Check if a tick position is on an off-beat
bool isOffBeat(int tick, int ticksPerBeat) {
  int ticksPerEighth = ticksPerBeat / 2;
  int positionInEighth = tick % ticksPerEighth;
  int eighthBeatIndex = (tick / ticksPerEighth) % 2;
  return (eighthBeatIndex == 1 && positionInEighth == 0);
}

// Musical scale intervals in semitones
std::vector<int> getScaleIntervals(int scaleType) {
  switch (scaleType) {
    case 0:  // Major
      return {0, 2, 4, 5, 7, 9, 11};
    case 1:  // Minor
      return {0, 2, 3, 5, 7, 8, 10};
    case 2:  // Dorian
      return {0, 2, 3, 5, 7, 9, 10};
    case 3:  // Lydian
      return {0, 2, 4, 6, 7, 9, 11};
    default:
      return {0, 2, 4, 5, 7, 9, 11};
  }
}

// Phase 8: Velocity scaling based on section energy for dynamics
int scaleVelocity(int baseVelocity, float sectionEnergy) {
  // intro/outro (0.2): 60-80
  // build (0.5): 80-95
  // drop (1.0): 90-110
  // break (0.4): 70-90
  
  int scaled;
  if (sectionEnergy < 0.3f) {
    // Intro/outro: soft
    scaled = 60 + static_cast<int>((baseVelocity - 60) * 0.3f);
  } else if (sectionEnergy < 0.6f) {
    // Build/break: medium
    scaled = 70 + static_cast<int>((baseVelocity - 70) * 0.6f);
  } else {
    // Drop: loud
    scaled = 90 + static_cast<int>((baseVelocity - 90) * 1.2f);
  }
  
  return std::max(40, std::min(120, scaled));
}

// Chord progression templates for different scale types
struct ChordProgression {
  std::vector<int> degrees;  // Scale degrees (0-6)
  std::string name;
};

// Phase 9: Get chord progressions based on scale type and genre
std::vector<ChordProgression> getProgressions(int scaleType, Genre genre = Genre::EDM_DROP) {
  if (genre == Genre::RAP) {
    // Rap/Trap: Simple 2-4 chord loops, often minor
    if (scaleType == 1 || scaleType == 2) {  // Minor or Dorian
      return {{{0, 5, 2, 6}, "i-VI-III-VII"},
              {{0, 6, 5, 6}, "i-VII-VI-VII"},
              {{0, 3, 5, 5}, "i-iv-VI-VI"}};
    } else {
      return {{{0, 4, 3, 4}, "I-V-IV-V"},
              {{0, 5, 3, 3}, "I-vi-IV-IV"}};
    }
  } else if (genre == Genre::RNB) {
    // R&B: Extended chords, jazzy progressions
    if (scaleType == 0 || scaleType == 3) {  // Major or Lydian
      return {{{1, 4, 0, 0}, "ii7-V7-Imaj7-Imaj7"},
              {{3, 2, 1, 4}, "IVmaj7-iii7-ii7-V7"},
              {{0, 4, 5, 3}, "I-V-vi-IV"}};  // Pop progression but works well
    } else {  // Minor or Dorian
      return {{{0, 3, 6, 5}, "i7-iv7-VII-VI"},
              {{0, 5, 3, 4}, "i-VI-iv-v7"}};
    }
  } else if (genre == Genre::HOUSE) {
    // House: Uplifting, repetitive progressions
    if (scaleType == 0 || scaleType == 3) {  // Major or Lydian
      return {{{0, 5, 3, 4}, "I-vi-IV-V"},  // Classic pop
              {{3, 4, 0, 5}, "IV-V-I-vi"},  // Uplifting
              {{0, 4, 5, 3}, "I-V-vi-IV"}};  // Modern house
    } else {
      return {{{0, 6, 3, 4}, "i-VII-iv-v"},
              {{0, 3, 5, 5}, "i-iv-VI-VI"}};
    }
  }
  
  // Original progressions for EDM genres
  if (scaleType == 0 || scaleType == 3) {
    // Major / Lydian progressions
    return {{{0, 5, 3, 4}, "I-vi-IV-V"},
            {{0, 4, 0, 5}, "I-V-I-vi"},
            {{0, 3, 4, 4}, "I-IV-V-V"}};
  } else {
    // Minor / Dorian progressions
    return {{{0, 3, 5, 5}, "i-iv-VI-VI"},
            {{0, 4, 3, 5}, "i-v-iv-VI"},
            {{0, 5, 3, 3}, "i-VI-iv-iv"}};
  }
}

// Overload for backward compatibility
std::vector<ChordProgression> getProgressions(int scaleType) {
  return getProgressions(scaleType, Genre::EDM_DROP);
}

// Random number generator for humanization
std::mt19937& getRng() {
  static std::mt19937 rng(42);  // Fixed seed for reproducibility
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

// Phase 9: Genre-specific drum pattern data
// General MIDI drum map constants
const int KICK = 36;
const int SNARE = 38;
const int CLAP = 39;
const int CLOSED_HAT = 42;
const int OPEN_HAT = 46;
const int CRASH = 49;
const int RIDE = 51;
const int TOM_LOW = 41;
const int TOM_MID = 47;
const int TOM_HIGH = 50;

// Phase 9: House drum patterns
DrumPattern getHousePattern(float energy) {
  DrumPattern pattern;
  pattern.name = "house_basic";
  
  // Four-on-the-floor kick (every beat)
  for (int beat = 0; beat < 4; ++beat) {
    pattern.hits.push_back({beat * 4, KICK, 100});
  }
  
  // Snare/clap on 2 and 4
  pattern.hits.push_back({4, SNARE, 95});   // Beat 2
  pattern.hits.push_back({12, SNARE, 95});  // Beat 4
  
  // Off-beat hi-hats (8th notes on the "and")
  for (int i = 0; i < 4; ++i) {
    pattern.hits.push_back({i * 4 + 2, CLOSED_HAT, 75});  // Off-beats
  }
  
  // Add 16th hats for higher energy
  if (energy > 0.6f) {
    for (int i = 0; i < 16; i += 2) {
      if (i % 4 != 0 && i % 4 != 2) {  // Fill in gaps
        pattern.hits.push_back({i, CLOSED_HAT, 60});
      }
    }
  }
  
  return pattern;
}

// Phase 9: Rap/Trap drum patterns
DrumPattern getTrapPattern(float energy) {
  DrumPattern pattern;
  pattern.name = "trap_808";
  
  // Syncopated kick pattern
  pattern.hits.push_back({0, KICK, 100});    // Beat 1
  pattern.hits.push_back({6, KICK, 85});     // "& of 2" (syncopated)
  pattern.hits.push_back({8, KICK, 95});     // Beat 3
  
  if (energy > 0.5f) {
    pattern.hits.push_back({14, KICK, 80});  // "a of 3" (syncopated)
  }
  
  // Snare on 2 & 4 (or just 3 for half-time feel)
  if (energy > 0.4f) {
    pattern.hits.push_back({4, SNARE, 100});   // Beat 2
    pattern.hits.push_back({12, SNARE, 100});  // Beat 4
  } else {
    pattern.hits.push_back({8, SNARE, 100});   // Beat 3 only (half-time)
  }
  
  // Ghost snares before backbeat
  if (energy > 0.5f) {
    pattern.hits.push_back({3, SNARE, 50});    // Ghost before beat 2
    pattern.hits.push_back({11, SNARE, 50});   // Ghost before beat 4
  }
  
  // Triplet hi-hat rolls
  for (int i = 0; i < 16; i += 2) {
    int vel = (i % 4 == 0) ? 70 : 55;  // Accent on beats
    pattern.hits.push_back({i, CLOSED_HAT, vel});
  }
  
  // Add occasional open hat
  if (energy > 0.6f) {
    pattern.hits.push_back({7, OPEN_HAT, 65});
    pattern.hits.push_back({15, OPEN_HAT, 65});
  }
  
  return pattern;
}

// Phase 9: R&B drum patterns
DrumPattern getRnBPattern(float energy) {
  DrumPattern pattern;
  pattern.name = "rnb_groove";
  
  // Softer kick pattern
  pattern.hits.push_back({0, KICK, 80});     // Beat 1
  pattern.hits.push_back({8, KICK, 75});     // Beat 3
  
  if (energy > 0.5f) {
    pattern.hits.push_back({6, KICK, 65});   // Syncopated kick
  }
  
  // Snare with ghost notes
  pattern.hits.push_back({4, SNARE, 85});    // Beat 2
  pattern.hits.push_back({12, SNARE, 85});   // Beat 4
  
  // Ghost snares (softer, creating groove)
  pattern.hits.push_back({2, SNARE, 45});    // Ghost
  pattern.hits.push_back({10, SNARE, 45});   // Ghost
  
  // Gentle hi-hats (sparse)
  for (int beat = 0; beat < 4; ++beat) {
    pattern.hits.push_back({beat * 4, CLOSED_HAT, 60});
    if (energy > 0.4f) {
      pattern.hits.push_back({beat * 4 + 2, CLOSED_HAT, 50});  // Off-beats
    }
  }
  
  // Ride cymbal for higher energy
  if (energy > 0.7f) {
    for (int i = 0; i < 16; i += 2) {
      pattern.hits.push_back({i, RIDE, 55});
    }
  }
  
  return pattern;
}

// Phase 9: Generate drums using pattern data + swing
void generateDrumsBarGenre(MidiWriter& midi, int trackIdx, int startTick,
                           int ticksPerBar, const GenreProfile& genre, 
                           float energy, float complexity, bool addFill = false) {
  int ticksPerBeat = ticksPerBar / 4;
  int ticksPer16th = ticksPerBeat / 4;
  int channel = 9;  // MIDI channel 10 (drums)
  
  // Get appropriate pattern based on genre
  DrumPattern pattern;
  if (genre.genre == Genre::HOUSE) {
    pattern = getHousePattern(energy);
  } else if (genre.genre == Genre::RAP) {
    pattern = getTrapPattern(energy);
  } else if (genre.genre == Genre::RNB) {
    pattern = getRnBPattern(energy);
  } else {
    // EDM patterns - use the existing logic via old function
    // (fallback to prevent duplicate code)
    return;  // Will use old generateDrumsBar
  }
  
  // Play pattern hits
  for (const auto& hit : pattern.hits) {
    int hitTick = startTick + hit.step * ticksPer16th;
    
    // Apply swing if genre uses it
    hitTick = applySwing(hitTick - startTick, ticksPerBeat, 
                         genre.useSwing, genre.swingAmount) + startTick;
    
    // Humanization
    int vel = hit.velocity + randomInt(-5, 5);
    vel = std::clamp(vel, 40, 127);
    
    // Add slight timing variation (except for kicks in house - keep those tight)
    int timingVar = 0;
    if (genre.genre != Genre::HOUSE || hit.note != KICK) {
      timingVar = randomInt(-3, 3);
    }
    
    midi.addNoteOn(trackIdx, hitTick + timingVar, channel, hit.note, vel);
    midi.addNoteOff(trackIdx, hitTick + timingVar + ticksPer16th, channel, hit.note);
  }
  
  // Add fills at section transitions
  if (addFill && energy > 0.3f) {
    int fillStart = startTick + ticksPerBar - ticksPerBeat;
    
    if (genre.genre == Genre::HOUSE) {
      // House: Snare roll
      for (int i = 0; i < 4; ++i) {
        int vel = 70 + i * 8;  // Crescendo
        midi.addNoteOn(trackIdx, fillStart + i * ticksPer16th, channel, SNARE, vel);
        midi.addNoteOff(trackIdx, fillStart + i * ticksPer16th + ticksPer16th/2, channel, SNARE);
      }
    } else if (genre.genre == Genre::RAP) {
      // Rap: Hi-hat roll
      for (int i = 0; i < 8; ++i) {
        int vel = 65 + i * 4;
        midi.addNoteOn(trackIdx, fillStart + i * (ticksPer16th/2), channel, CLOSED_HAT, vel);
        midi.addNoteOff(trackIdx, fillStart + i * (ticksPer16th/2) + 20, channel, CLOSED_HAT);
      }
    } else if (genre.genre == Genre::RNB) {
      // R&B: Tom fill (melodic)
      int toms[] = {TOM_HIGH, TOM_MID, TOM_LOW, TOM_LOW};
      for (int i = 0; i < 4; ++i) {
        int vel = 75 + i * 5;
        midi.addNoteOn(trackIdx, fillStart + i * ticksPer16th, channel, toms[i], vel);
        midi.addNoteOff(trackIdx, fillStart + i * ticksPer16th + ticksPer16th, channel, toms[i]);
      }
    }
  }
}

// Original drum generator (for EDM genres)
void generateDrumsBar(MidiWriter& midi, int trackIdx, int startTick,
                      int ticksPerBar, GrooveType groove, float energy,
                      float complexity, bool addFill = false) {
  int ticksPerBeat = ticksPerBar / 4;
  int channel = 9;  // MIDI channel 10 (9 in 0-indexed) = drums

  int baseVelocity = 80 + static_cast<int>(energy * 30);

  if (groove == GrooveType::CHILL) {
    // Sparse, laid-back pattern
    // Kick on 1 and 3
    midi.addNoteOn(trackIdx, startTick, channel, KICK, baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat / 2, channel, KICK);

    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, KICK,
                   baseVelocity - 10);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 + ticksPerBeat / 2,
                    channel, KICK);

    // Sparse hi-hats
    if (complexity > 0.3f) {
      for (int beat = 0; beat < 4; ++beat) {
        int vel = baseVelocity - 20 + randomInt(-5, 5);
        midi.addNoteOn(trackIdx, startTick + beat * ticksPerBeat, channel,
                       CLOSED_HAT, vel);
        midi.addNoteOff(trackIdx,
                        startTick + beat * ticksPerBeat + ticksPerBeat / 4,
                        channel, CLOSED_HAT);
      }
    }

  } else if (groove == GrooveType::DRIVING) {
    // Energetic 4-on-floor pattern
    // Kick on every beat
    for (int beat = 0; beat < 4; ++beat) {
      int vel = baseVelocity + randomInt(-5, 5);
      midi.addNoteOn(trackIdx, startTick + beat * ticksPerBeat, channel, KICK,
                     vel);
      midi.addNoteOff(trackIdx,
                      startTick + beat * ticksPerBeat + ticksPerBeat / 2,
                      channel, KICK);
    }

    // Snare on 2 and 4
    midi.addNoteOn(trackIdx, startTick + ticksPerBeat, channel, SNARE,
                   baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat + ticksPerBeat / 2,
                    channel, SNARE);

    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 3, channel, SNARE,
                   baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 3 + ticksPerBeat / 2,
                    channel, SNARE);

    // 8th note hi-hats
    for (int i = 0; i < 8; ++i) {
      int vel = baseVelocity - 10 + randomInt(-5, 5);
      int hat = (i % 4 == 3 && complexity > 0.6f) ? OPEN_HAT : CLOSED_HAT;
      midi.addNoteOn(trackIdx, startTick + i * (ticksPerBeat / 2), channel, hat,
                     vel);
      midi.addNoteOff(trackIdx,
                      startTick + i * (ticksPerBeat / 2) + ticksPerBeat / 4,
                      channel, hat);
    }

  } else {
    // STRAIGHT: Standard rock/pop beat
    // Kick on 1 and 3
    midi.addNoteOn(trackIdx, startTick, channel, KICK, baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat / 2, channel, KICK);

    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, KICK,
                   baseVelocity - 5);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 + ticksPerBeat / 2,
                    channel, KICK);

    // Snare on 2 and 4
    midi.addNoteOn(trackIdx, startTick + ticksPerBeat, channel, SNARE,
                   baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat + ticksPerBeat / 2,
                    channel, SNARE);

    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 3, channel, SNARE,
                   baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 3 + ticksPerBeat / 2,
                    channel, SNARE);

    // Quarter note hi-hats
    for (int beat = 0; beat < 4; ++beat) {
      int vel = baseVelocity - 15 + randomInt(-5, 5);
      midi.addNoteOn(trackIdx, startTick + beat * ticksPerBeat, channel,
                     CLOSED_HAT, vel);
      midi.addNoteOff(trackIdx,
                      startTick + beat * ticksPerBeat + ticksPerBeat / 4,
                      channel, CLOSED_HAT);
    }
  }
  
  // Phase 8: Add fills at section transitions
  if (addFill && energy > 0.3f) {
    // Snare roll in the last half-beat
    int fillStart = startTick + ticksPerBar - ticksPerBeat;
    int sixteenthNote = ticksPerBeat / 4;
    
    for (int i = 0; i < 4; ++i) {
      int vel = baseVelocity - 10 + i * 5;  // Crescendo
      midi.addNoteOn(trackIdx, fillStart + i * sixteenthNote, channel, SNARE, vel);
      midi.addNoteOff(trackIdx, fillStart + i * sixteenthNote + sixteenthNote / 2, channel, SNARE);
    }
    
    // Crash on the downbeat of next section (added by next bar generation)
  }
}

// Generate bass line for one bar (Phase 8: Enhanced with EDM-style patterns)
void generateBassBar(MidiWriter& midi, int trackIdx, int startTick,
                     int ticksPerBar, int rootNote, int chordDegree,
                     const std::vector<int>& scale, int channel, float energy,
                     float complexity) {
  int ticksPerBeat = ticksPerBar / 4;
  int baseVelocity = 70 + static_cast<int>(energy * 25);

  // Bass plays root of current chord, octave down
  int bassNote = rootNote - 12 + scale[chordDegree % scale.size()];
  int fifthNote = rootNote - 12 + scale[(chordDegree + 4) % scale.size()];
  int octaveUp = bassNote + 12;

  if (energy < 0.3f) {
    // Low energy: simple whole notes or half notes
    midi.addNoteOn(trackIdx, startTick, channel, bassNote, baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, bassNote);
  } else if (energy < 0.6f) {
    // Medium energy: root on 1 and 3 with octave variation
    midi.addNoteOn(trackIdx, startTick, channel, bassNote, baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 - 10, channel,
                    bassNote);

    // Octave jump on beat 3
    int note2 = (complexity > 0.4f) ? octaveUp : bassNote;
    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, note2,
                   baseVelocity - 5);
    midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, note2);
  } else {
    // High energy: Walking bass with 8th notes (EDM-style)
    // Pattern: root - fifth - octave - fifth (creates movement)
    int eighthNote = ticksPerBeat / 2;
    
    // Beat 1: root
    midi.addNoteOn(trackIdx, startTick, channel, bassNote, baseVelocity);
    midi.addNoteOff(trackIdx, startTick + eighthNote - 5, channel, bassNote);
    
    // Beat 1.5: fifth
    midi.addNoteOn(trackIdx, startTick + eighthNote, channel, fifthNote,
                   baseVelocity - 10);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat - 5, channel, fifthNote);
    
    // Beat 2: root (accented)
    midi.addNoteOn(trackIdx, startTick + ticksPerBeat, channel, bassNote,
                   baseVelocity - 5);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat + eighthNote - 5, channel,
                    bassNote);
    
    // Beat 3: octave up (creates lift)
    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, octaveUp,
                   baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 + eighthNote - 5,
                    channel, octaveUp);
    
    // Beat 3.5: fifth
    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2 + eighthNote, channel,
                   fifthNote, baseVelocity - 10);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 3 - 5, channel,
                    fifthNote);
    
    // Beat 4: root (leads back to next bar)
    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 3, channel, bassNote,
                   baseVelocity - 5);
    midi.addNoteOff(trackIdx, startTick + ticksPerBar - 5, channel, bassNote);
  }
}

// Phase 9: Build extended chord voicings for R&B/Jazz styles
std::vector<int> buildExtendedChord(int rootNote, int chordDegree,
                                     const std::vector<int>& scale,
                                     Genre genre, float complexity) {
  std::vector<int> chordNotes;
  
  // Always include root, third, fifth
  chordNotes.push_back(rootNote + scale[chordDegree % scale.size()]);
  chordNotes.push_back(rootNote + scale[(chordDegree + 2) % scale.size()]);
  chordNotes.push_back(rootNote + scale[(chordDegree + 4) % scale.size()]);
  
  if (genre == Genre::RNB) {
    // R&B: Add 7th and optionally 9th/11th
    chordNotes.push_back(rootNote + scale[(chordDegree + 6) % scale.size()]);  // 7th
    
    if (complexity > 0.6f) {
      // Add 9th (2nd an octave up)
      chordNotes.push_back(rootNote + 12 + scale[(chordDegree + 1) % scale.size()]);
    }
    
    if (complexity > 0.8f) {
      // Add 11th (4th an octave up) for very lush sound
      chordNotes.push_back(rootNote + 12 + scale[(chordDegree + 3) % scale.size()]);
    }
  } else {
    // Other genres: Add 7th if complexity is high
    if (complexity > 0.6f) {
      chordNotes.push_back(rootNote + scale[(chordDegree + 6) % scale.size()]);
    }
  }
  
  return chordNotes;
}

// Generate chord voicing for one bar (Phase 8: Rhythmic variation based on energy)
void generateChordBar(MidiWriter& midi, int trackIdx, int startTick,
                      int ticksPerBar, int rootNote, int chordDegree,
                      const std::vector<int>& scale, int channel, float energy,
                      float complexity) {
  int ticksPerBeat = ticksPerBar / 4;
  int baseVelocity = 60 + static_cast<int>(energy * 20);

  // Build triad: root, third, fifth
  std::vector<int> chordNotes;
  chordNotes.push_back(rootNote + scale[chordDegree % scale.size()]);
  chordNotes.push_back(rootNote + scale[(chordDegree + 2) % scale.size()]);
  chordNotes.push_back(rootNote + scale[(chordDegree + 4) % scale.size()]);
  
  // Add 7th for complexity
  if (complexity > 0.6f) {
    chordNotes.push_back(rootNote + scale[(chordDegree + 6) % scale.size()]);
  }

  if (energy < 0.3f) {
    // Intro/break: long sustained chords (2 bars worth of sustain)
    for (int note : chordNotes) {
      midi.addNoteOn(trackIdx, startTick, channel, note, baseVelocity - 10);
      midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, note);
    }
  } else if (energy < 0.7f) {
    // Build: half-note chords (on beats 1 and 3)
    for (int note : chordNotes) {
      midi.addNoteOn(trackIdx, startTick, channel, note, baseVelocity);
      midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 - 10, channel, note);

      midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, note,
                     baseVelocity - 5);
      midi.addNoteOff(trackIdx, startTick + ticksPerBar - 10, channel, note);
    }
  } else {
    // Drop: rhythmic quarter-note stabs (EDM-style)
    // Pattern: 1, 1.5, 2, 2.5, 3, 4 (syncopated)
    int eighthNote = ticksPerBeat / 2;
    int stabs[] = {0, eighthNote, ticksPerBeat, ticksPerBeat + eighthNote,
                   ticksPerBeat * 2, ticksPerBeat * 3};
    int stabbedVel = baseVelocity + 5;  // Accented for drop
    
    for (int stab : stabs) {
      for (int note : chordNotes) {
        midi.addNoteOn(trackIdx, startTick + stab, channel, note, stabbedVel);
        midi.addNoteOff(trackIdx, startTick + stab + eighthNote - 10, channel, note);
      }
      stabbedVel -= 3;  // Slight velocity variation
    }
  }
}

// Phase 8: Motif-based lead/hook generator
void generateMelodyBar(MidiWriter& midi, int trackIdx, int startTick,
                       int ticksPerBar, int rootNote, int chordDegree,
                       const std::vector<int>& scale, int channel,
                       float moodScore, int& melodicState) {
  int ticksPerBeat = ticksPerBar / 4;
  int baseVelocity = 75 + static_cast<int>(moodScore * 20);

  // Create a 4-note motif from scale degrees 0, 2, 4 (root, third, fifth)
  // This creates a memorable, singable hook
  std::vector<int> motifDegrees;
  
  if (moodScore > 0.6f) {
    // Happy/bright: ascending motif (0-2-4-5 or similar)
    motifDegrees = {0, 2, 4, 5, 4, 2};  // Up and back down
  } else if (moodScore > 0.4f) {
    // Neutral: stepwise with repetition
    motifDegrees = {0, 2, 2, 4, 4, 2};  // Repetitive hook
  } else {
    // Dark/moody: descending or sparse
    motifDegrees = {4, 2, 0, 2};  // Descending
  }
  
  // Rhythm: use 8th notes for energetic feel, quarter notes for chill
  bool use16ths = (moodScore > 0.7f);
  int noteDuration = use16ths ? (ticksPerBeat / 4) : (ticksPerBeat / 2);
  
  int tick = startTick;
  for (size_t i = 0; i < motifDegrees.size() && tick < startTick + ticksPerBar; ++i) {
    // Calculate note from scale degree relative to chord
    int degree = (chordDegree + motifDegrees[i]) % scale.size();
    int note = rootNote + 12 + scale[degree];  // Octave up from root
    
    // Add slight transposition based on melodic state (creates variation)
    if (melodicState > 3) {
      note += 12;  // Jump up an octave for variation
    } else if (melodicState < -2) {
      note -= 12;  // Down for contrast
    }
    
    // Ensure note stays in reasonable range
    note = std::max(60, std::min(84, note));
    
    // Add rhythmic variation: some notes are accented or sustained
    int duration = noteDuration;
    int velocity = baseVelocity;
    
    if (i == 0 || i == motifDegrees.size() - 1) {
      // Accent first and last notes of motif
      velocity += 10;
      duration = noteDuration * 3 / 2;  // Slightly longer
    }
    
    // Humanization: slight velocity variation
    velocity += randomInt(-5, 5);
    
    midi.addNoteOn(trackIdx, tick, channel, note, velocity);
    midi.addNoteOff(trackIdx, tick + duration - 5, channel, note);
    
    tick += noteDuration;
  }
  
  // Update melodic state for variation across bars
  melodicState += randomInt(-1, 2);
  melodicState = std::max(-3, std::min(4, melodicState));
}

// Generate pad (sustained chords) for one bar
void generatePadBar(MidiWriter& midi, int trackIdx, int startTick,
                    int ticksPerBar, int rootNote, int chordDegree,
                    const std::vector<int>& scale, int channel,
                    float moodScore) {
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

}  // anonymous namespace

void composeSongToMidi(const SongSpec& spec, const std::string& midiPath) {
  MidiWriter midi(480);  // 480 ticks per quarter note
  midi.setTempo(spec.tempoBpm);
  midi.setTimeSignature(4, 4);

  // Calculate timing
  int ticksPerQuarter = 480;
  int ticksPerBar = ticksPerQuarter * 4;  // 4/4 time

  // Get scale intervals
  std::vector<int> scale = getScaleIntervals(spec.scaleType);

  // Phase 9: Get genre-aware chord progression
  auto progressions = getProgressions(spec.scaleType, spec.genreProfile.genre);
  auto progression =
      progressions[0];  // Use first progression (can be randomized)

  // Create tracks with TrackRole enum support
  std::map<TrackRole, int> trackIndices;
  std::map<TrackRole, int> channelMap;

  for (const auto& trackSpec : spec.tracks) {
    const char* roleName = trackRoleName(trackSpec.role);
    int trackIdx = midi.addTrack(roleName);
    trackIndices[trackSpec.role] = trackIdx;
    channelMap[trackSpec.role] = trackSpec.midiChannel;

    // Add program change at start (except for drums)
    if (trackSpec.role != TrackRole::DRUMS) {
      midi.addProgramChange(trackIdx, 0, trackSpec.midiChannel,
                            trackSpec.program);
    }
  }

  // Compose each section
  int currentTick = 0;
  int melodicState = 2;  // Start on third degree for melody

  for (size_t secIdx = 0; secIdx < spec.sections.size(); ++secIdx) {
    const auto& section = spec.sections[secIdx];
    float sectionEnergy = section.targetEnergy;
    
    // Phase 9: Get section activity based on genre
    SectionActivity activity = getSectionActivity(spec.genreProfile, section, spec.moodScore);
    
    // Determine if this is the last section
    bool isLastSection = (secIdx == spec.sections.size() - 1);
    
    // Phase 8: Determine if lead should be active in this section
    bool leadActive = activity.lead;

    // Generate bars for this section
    for (int bar = 0; bar < section.bars; ++bar) {
      // Current chord from progression
      int progressionIndex = bar % progression.degrees.size();
      int chordDegree = progression.degrees[progressionIndex];
      
      // Check if this is the last bar of a section (for fills)
      bool isLastBarOfSection = (bar == section.bars - 1) && !isLastSection;
      
      // Activate lead in second half of build sections (genre-specific override)
      bool leadActiveThisBar = leadActive;
      if (!leadActiveThisBar && (section.name == "build" || section.name == "build2")) {
        leadActiveThisBar = (bar >= section.bars / 2) && activity.lead;
      }

      // Generate each track for this bar
      for (const auto& trackSpec : spec.tracks) {
        int trackIdx = trackIndices[trackSpec.role];
        int channel = channelMap[trackSpec.role];

        switch (trackSpec.role) {
          case TrackRole::DRUMS:
            // Only generate if active in this section
            if (activity.drums) {
              // Phase 9: Use genre-specific drum generator for Rap/House/RnB
              if (spec.genreProfile.genre == Genre::HOUSE ||
                  spec.genreProfile.genre == Genre::RAP ||
                  spec.genreProfile.genre == Genre::RNB) {
                generateDrumsBarGenre(midi, trackIdx, currentTick, ticksPerBar,
                                      spec.genreProfile, sectionEnergy, 
                                      trackSpec.complexity, isLastBarOfSection);
              } else {
                // EDM genres use original generator
                generateDrumsBar(midi, trackIdx, currentTick, ticksPerBar,
                                 spec.groove, sectionEnergy, trackSpec.complexity,
                                 isLastBarOfSection);
              }
            }
            break;
          case TrackRole::BASS:
            if (activity.bass) {
              generateBassBar(midi, trackIdx, currentTick, ticksPerBar,
                              spec.rootMidiNote, chordDegree, scale, channel,
                              sectionEnergy, trackSpec.complexity);
            }
            break;
          case TrackRole::CHORDS:
            if (activity.chords) {
              generateChordBar(midi, trackIdx, currentTick, ticksPerBar,
                               spec.rootMidiNote, chordDegree, scale, channel,
                               sectionEnergy, trackSpec.complexity);
            }
            break;
          case TrackRole::LEAD:
            // Only generate lead if active in this section/bar
            if (leadActiveThisBar && activity.lead) {
              generateMelodyBar(midi, trackIdx, currentTick, ticksPerBar,
                                spec.rootMidiNote, chordDegree, scale, channel,
                                spec.moodScore, melodicState);
            }
            break;
          case TrackRole::PAD:
            if (activity.pad) {
              generatePadBar(midi, trackIdx, currentTick, ticksPerBar,
                             spec.rootMidiNote, chordDegree, scale, channel,
                             spec.moodScore);
            }
            break;
          case TrackRole::FX:
            // Phase 9: FX triggers for transitions
            // TODO: Add reverse cymbals, impacts, sweeps at section boundaries
            break;
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

std::map<std::string, std::string> composeSongToStems(
    const SongSpec& spec, const std::string& outputDir) {
  // Create a MIDI writer
  MidiWriter midi(480);
  midi.setTempo(spec.tempoBpm);
  midi.setTimeSignature(4, 4);

  // Generate composition (reusing logic from composeSongToMidi)
  std::vector<int> scale = getScaleIntervals(spec.scaleType);
  int rootNote = spec.rootMidiNote;
  
  // Add tracks
  std::vector<std::string> trackNames;
  std::vector<int> trackIndices;

  for (const auto& track : spec.tracks) {
    const char* roleName = trackRoleName(track.role);
    int trackIdx = midi.addTrack(roleName);
    trackNames.push_back(roleName);
    trackIndices.push_back(trackIdx);

    // Set instrument (except for drums)
    if (track.role != TrackRole::DRUMS) {
      midi.addProgramChange(trackIdx, 0, track.midiChannel, track.program);
    }
  }

  // Generate musical content for each section
  int currentTick = 0;
  int ticksPerBeat = 480;
  int ticksPerBar = ticksPerBeat * 4;

  for (const auto& section : spec.sections) {
    int sectionTicks = ticksPerBar * section.bars;

    // Generate content for each track
    for (size_t i = 0; i < spec.tracks.size(); ++i) {
      const auto& track = spec.tracks[i];
      int trackIdx = trackIndices[i];

      // Different patterns based on track role
      switch (track.role) {
        case TrackRole::DRUMS:
          // Drum pattern (simplified)
          for (int bar = 0; bar < section.bars; ++bar) {
            int barStart = currentTick + bar * ticksPerBar;

            // Kick on beats 1 and 3
            midi.addNoteOn(trackIdx, barStart, 9, 36, 100);
            midi.addNoteOff(trackIdx, barStart + ticksPerBeat / 2, 9, 36);

            midi.addNoteOn(trackIdx, barStart + ticksPerBeat * 2, 9, 36, 100);
            midi.addNoteOff(
                trackIdx, barStart + ticksPerBeat * 2 + ticksPerBeat / 2, 9, 36);

            // Snare on beats 2 and 4
            midi.addNoteOn(trackIdx, barStart + ticksPerBeat, 9, 38, 90);
            midi.addNoteOff(trackIdx, barStart + ticksPerBeat + ticksPerBeat / 2,
                            9, 38);

            midi.addNoteOn(trackIdx, barStart + ticksPerBeat * 3, 9, 38, 90);
            midi.addNoteOff(
                trackIdx, barStart + ticksPerBeat * 3 + ticksPerBeat / 2, 9, 38);
          }
          break;
          
        case TrackRole::BASS:
          // Bass line - root note pattern
          for (int bar = 0; bar < section.bars; ++bar) {
            int barStart = currentTick + bar * ticksPerBar;
            int bassNote = rootNote - 12;  // One octave below root

            midi.addNoteOn(trackIdx, barStart, track.midiChannel, bassNote, 80);
            midi.addNoteOff(trackIdx, barStart + ticksPerBeat * 2, track.midiChannel, bassNote);

            midi.addNoteOn(trackIdx, barStart + ticksPerBeat * 2, track.midiChannel, bassNote, 80);
            midi.addNoteOff(trackIdx, barStart + ticksPerBeat * 4, track.midiChannel, bassNote);
          }
          break;
          
        case TrackRole::CHORDS:
          // Chord progression
          {
            std::vector<ChordProgression> progs = getProgressions(spec.scaleType, spec.genreProfile.genre);
            const auto& prog = progs[0];

            for (int bar = 0; bar < section.bars; ++bar) {
              int barStart = currentTick + bar * ticksPerBar;
              int chordIdx = bar % prog.degrees.size();
              int degree = prog.degrees[chordIdx];
              int chordRoot = rootNote + scale[degree];

              // Triad
              std::vector<int> chord = {chordRoot, chordRoot + scale[2],
                                        chordRoot + scale[4]};

              for (int note : chord) {
                midi.addNoteOn(trackIdx, barStart, track.midiChannel, note, 70);
                midi.addNoteOff(trackIdx, barStart + ticksPerBar, track.midiChannel, note);
              }
            }
          }
          break;
          
        case TrackRole::LEAD:
          // Melody line
          {
            std::mt19937 rng(42);
            std::uniform_int_distribution<> noteDist(0, scale.size() - 1);

            for (int bar = 0; bar < section.bars; ++bar) {
              int barStart = currentTick + bar * ticksPerBar;

              for (int beat = 0; beat < 4; ++beat) {
                int noteStart = barStart + beat * ticksPerBeat;
                int scaleIdx = noteDist(rng);
                int note = rootNote + 12 + scale[scaleIdx];  // One octave up

                midi.addNoteOn(trackIdx, noteStart, track.midiChannel, note, 75);
                midi.addNoteOff(trackIdx, noteStart + ticksPerBeat * 3 / 4, track.midiChannel, note);
              }
            }
          }
          break;
          
        case TrackRole::PAD:
          // Sustained pad chords
          for (int bar = 0; bar < section.bars; bar += 2) {
            int barStart = currentTick + bar * ticksPerBar;

            // Sustained chord
            std::vector<int> padChord = {rootNote, rootNote + scale[2],
                                         rootNote + scale[4],
                                         rootNote + 12 + scale[1]};

            for (int note : padChord) {
              midi.addNoteOn(trackIdx, barStart, track.midiChannel, note, 60);
              midi.addNoteOff(trackIdx, barStart + ticksPerBar * 2, track.midiChannel, note);
            }
          }
          break;
          
        case TrackRole::FX:
          // TODO: FX track implementation
          break;
      }
    }

    currentTick += sectionTicks;
  }

  // Write separate stem files
  return midi.writeSeparateStems(outputDir);
}
