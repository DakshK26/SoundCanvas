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

std::vector<ChordProgression> getProgressions(int scaleType) {
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

// Generate drums for one bar
void generateDrumsBar(MidiWriter& midi, int trackIdx, int startTick,
                      int ticksPerBar, GrooveType groove, float energy,
                      float complexity, bool addFill = false) {
  int ticksPerBeat = ticksPerBar / 4;
  int channel = 9;  // MIDI channel 10 (9 in 0-indexed) = drums

  // General MIDI drum map
  const int kick = 36;
  const int snare = 38;
  const int closedHat = 42;
  const int openHat = 46;
  const int crash = 49;
  const int ride = 51;

  int baseVelocity = 80 + static_cast<int>(energy * 30);

  if (groove == GrooveType::CHILL) {
    // Sparse, laid-back pattern
    // Kick on 1 and 3
    midi.addNoteOn(trackIdx, startTick, channel, kick, baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat / 2, channel, kick);

    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, kick,
                   baseVelocity - 10);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 + ticksPerBeat / 2,
                    channel, kick);

    // Sparse hi-hats
    if (complexity > 0.3f) {
      for (int beat = 0; beat < 4; ++beat) {
        int vel = baseVelocity - 20 + randomInt(-5, 5);
        midi.addNoteOn(trackIdx, startTick + beat * ticksPerBeat, channel,
                       closedHat, vel);
        midi.addNoteOff(trackIdx,
                        startTick + beat * ticksPerBeat + ticksPerBeat / 4,
                        channel, closedHat);
      }
    }

  } else if (groove == GrooveType::DRIVING) {
    // Energetic 4-on-floor pattern
    // Kick on every beat
    for (int beat = 0; beat < 4; ++beat) {
      int vel = baseVelocity + randomInt(-5, 5);
      midi.addNoteOn(trackIdx, startTick + beat * ticksPerBeat, channel, kick,
                     vel);
      midi.addNoteOff(trackIdx,
                      startTick + beat * ticksPerBeat + ticksPerBeat / 2,
                      channel, kick);
    }

    // Snare on 2 and 4
    midi.addNoteOn(trackIdx, startTick + ticksPerBeat, channel, snare,
                   baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat + ticksPerBeat / 2,
                    channel, snare);

    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 3, channel, snare,
                   baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 3 + ticksPerBeat / 2,
                    channel, snare);

    // 8th note hi-hats
    for (int i = 0; i < 8; ++i) {
      int vel = baseVelocity - 10 + randomInt(-5, 5);
      int hat = (i % 4 == 3 && complexity > 0.6f) ? openHat : closedHat;
      midi.addNoteOn(trackIdx, startTick + i * (ticksPerBeat / 2), channel, hat,
                     vel);
      midi.addNoteOff(trackIdx,
                      startTick + i * (ticksPerBeat / 2) + ticksPerBeat / 4,
                      channel, hat);
    }

  } else {
    // STRAIGHT: Standard rock/pop beat
    // Kick on 1 and 3
    midi.addNoteOn(trackIdx, startTick, channel, kick, baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat / 2, channel, kick);

    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 2, channel, kick,
                   baseVelocity - 5);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 2 + ticksPerBeat / 2,
                    channel, kick);

    // Snare on 2 and 4
    midi.addNoteOn(trackIdx, startTick + ticksPerBeat, channel, snare,
                   baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat + ticksPerBeat / 2,
                    channel, snare);

    midi.addNoteOn(trackIdx, startTick + ticksPerBeat * 3, channel, snare,
                   baseVelocity);
    midi.addNoteOff(trackIdx, startTick + ticksPerBeat * 3 + ticksPerBeat / 2,
                    channel, snare);

    // Quarter note hi-hats
    for (int beat = 0; beat < 4; ++beat) {
      int vel = baseVelocity - 15 + randomInt(-5, 5);
      midi.addNoteOn(trackIdx, startTick + beat * ticksPerBeat, channel,
                     closedHat, vel);
      midi.addNoteOff(trackIdx,
                      startTick + beat * ticksPerBeat + ticksPerBeat / 4,
                      channel, closedHat);
    }
  }
  
  // Phase 8: Add fills at section transitions
  if (addFill && energy > 0.3f) {
    // Snare roll in the last half-beat
    int fillStart = startTick + ticksPerBar - ticksPerBeat;
    int sixteenthNote = ticksPerBeat / 4;
    
    for (int i = 0; i < 4; ++i) {
      int vel = baseVelocity - 10 + i * 5;  // Crescendo
      midi.addNoteOn(trackIdx, fillStart + i * sixteenthNote, channel, snare, vel);
      midi.addNoteOff(trackIdx, fillStart + i * sixteenthNote + sixteenthNote / 2, channel, snare);
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

  // Get chord progression
  auto progressions = getProgressions(spec.scaleType);
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
    
    // Determine if this is the last section
    bool isLastSection = (secIdx == spec.sections.size() - 1);
    
    // Phase 8: Determine if lead should be active in this section
    bool leadActive = false;
    if (section.name == "drop" || section.name == "outro") {
      leadActive = true;  // Always active in drop and outro
    } else if (section.name == "build" || section.name == "build2") {
      // Active in second half of build
      leadActive = false;  // Will be enabled per-bar below
    }

    // Generate bars for this section
    for (int bar = 0; bar < section.bars; ++bar) {
      // Current chord from progression
      int progressionIndex = bar % progression.degrees.size();
      int chordDegree = progression.degrees[progressionIndex];
      
      // Check if this is the last bar of a section (for fills)
      bool isLastBarOfSection = (bar == section.bars - 1) && !isLastSection;
      
      // Activate lead in second half of build sections
      bool leadActiveThisBar = leadActive;
      if (!leadActiveThisBar && (section.name == "build" || section.name == "build2")) {
        leadActiveThisBar = (bar >= section.bars / 2);
      }

      // Generate each track for this bar
      for (const auto& trackSpec : spec.tracks) {
        int trackIdx = trackIndices[trackSpec.role];
        int channel = channelMap[trackSpec.role];

        switch (trackSpec.role) {
          case TrackRole::DRUMS:
            generateDrumsBar(midi, trackIdx, currentTick, ticksPerBar,
                             spec.groove, sectionEnergy, trackSpec.complexity,
                             isLastBarOfSection);
            break;
          case TrackRole::BASS:
            generateBassBar(midi, trackIdx, currentTick, ticksPerBar,
                            spec.rootMidiNote, chordDegree, scale, channel,
                            sectionEnergy, trackSpec.complexity);
            break;
          case TrackRole::CHORDS:
            generateChordBar(midi, trackIdx, currentTick, ticksPerBar,
                             spec.rootMidiNote, chordDegree, scale, channel,
                             sectionEnergy, trackSpec.complexity);
            break;
          case TrackRole::LEAD:
            // Only generate lead if active in this section/bar
            if (leadActiveThisBar) {
              generateMelodyBar(midi, trackIdx, currentTick, ticksPerBar,
                                spec.rootMidiNote, chordDegree, scale, channel,
                                spec.moodScore, melodicState);
            }
            break;
          case TrackRole::PAD:
            generatePadBar(midi, trackIdx, currentTick, ticksPerBar,
                           spec.rootMidiNote, chordDegree, scale, channel,
                           spec.moodScore);
            break;
          case TrackRole::FX:
            // TODO: FX track implementation
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
            std::vector<ChordProgression> progs = getProgressions(spec.scaleType);
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
