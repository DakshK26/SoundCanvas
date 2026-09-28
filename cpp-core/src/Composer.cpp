// how it works: go bar by bar -> grab this bar's chord from the progression -> play each
// part's 16 step pattern over it.
// section energy = which parts are on. intro is mostly chords + pad, drop is everything
#include "Composer.hpp"

#include <vector>

#include "MidiWriter.hpp"
#include "MusicTheory.hpp"

using namespace music;

namespace {

// energy thresholds for each part (rough, nothing scientific)
constexpr float BASS_MIN_ENERGY = 0.3f;      // quietest intros lose the bass
constexpr float DRUMS_MIN_ENERGY = 0.4f;     // no beat in intro/outro usually
constexpr float LEAD_MIN_ENERGY = 0.7f;      // melody only in drops
constexpr float OPEN_HAT_MIN_ENERGY = 0.8f;  // open hats = extra, only when it's going hard

// 1 channel per part bc program change (instrument) is per channel in midi
constexpr int BASS_CHANNEL = 0;
constexpr int CHORD_CHANNEL = 1;
constexpr int LEAD_CHANNEL = 2;
constexpr int PAD_CHANNEL = 3;

// tiny gap before each note ends so the same note played twice in a row actually
// re-triggers instead of sounding like one long note
constexpr int NOTE_GAP_TICKS = 10;

// lead is in 8ths = 2 steps each
constexpr int STEPS_PER_EIGHTH = 2;

struct Tracks {
  int drums, bass, chords, lead, pad;
};

// velocity (1-127) goes 50 -> 110 w/ energy
int velocityFor(float energy) { return 50 + static_cast<int>(energy * 60.0f); }

// degree 7 in a 7 note scale = root an octave up, so wrap w/ / and %
int scaleNote(int root, const std::vector<int>& scale, int degree) {
  int size = static_cast<int>(scale.size());
  return root + (degree / size) * SEMITONES_PER_OCTAVE + scale[degree % size];
}

// parses a pattern string -> play(startStep, lengthInSteps, symbol) per note.
// '-' after a note extends it. all the play* functions below use this
template <typename PlayFn>
void forEachNote(const std::string& pattern, PlayFn play) {
  for (int step = 0; step < static_cast<int>(pattern.size()); ++step) {
    char symbol = pattern[step];
    if (symbol == '.' || symbol == '-') continue;
    int length = 1;
    while (step + length < static_cast<int>(pattern.size()) && pattern[step + length] == '-') {
      ++length;
    }
    play(step, length, symbol);
  }
}

// 1 drum sound, hit on every x
void playDrum(MidiWriter& midi, int track, int barTick, const std::string& pattern, int drum,
              int velocity) {
  forEachNote(pattern, [&](int step, int, char) {
    midi.addNote(track, barTick + step * TICKS_PER_STEP, TICKS_PER_STEP, DRUM_CHANNEL, drum,
                 velocity);
  });
}

// snare roll on the last beat (4 16ths) right before a louder section
void playFill(MidiWriter& midi, int track, int barTick, int snare, int velocity) {
  for (int step = STEPS_PER_BAR - 4; step < STEPS_PER_BAR; ++step) {
    midi.addNote(track, barTick + step * TICKS_PER_STEP, TICKS_PER_STEP, DRUM_CHANNEL, snare,
                 velocity);
  }
}

// bass sits an octave below the chord. R root, F fifth, O = back up to chord octave
void playBass(MidiWriter& midi, int track, int barTick, const std::string& pattern,
              int chordRoot, int chordFifth, int velocity) {
  int bassRoot = chordRoot - SEMITONES_PER_OCTAVE;
  forEachNote(pattern, [&](int step, int length, char symbol) {
    int note = symbol == 'F' ? chordFifth - SEMITONES_PER_OCTAVE
             : symbol == 'O' ? chordRoot
                             : bassRoot;
    midi.addNote(track, barTick + step * TICKS_PER_STEP,
                 length * TICKS_PER_STEP - NOTE_GAP_TICKS, BASS_CHANNEL, note, velocity);
  });
}

// whole triad on every x
void playChords(MidiWriter& midi, int track, int barTick, const std::string& pattern,
                const std::vector<int>& chord, int velocity) {
  forEachNote(pattern, [&](int step, int length, char) {
    for (int note : chord) {
      midi.addNote(track, barTick + step * TICKS_PER_STEP,
                   length * TICKS_PER_STEP - NOTE_GAP_TICKS, CHORD_CHANNEL, note, velocity);
    }
  });
}

// melody an octave up. it's relative to the chord degree so it follows the chords
// instead of playing the same notes over everything
void playLead(MidiWriter& midi, int track, int barTick, const SongPlan& plan, int chordDegree,
              int velocity) {
  const GenreTemplate& genre = *plan.genre;
  int leadRoot = plan.rootNote + SEMITONES_PER_OCTAVE;
  int eighthTicks = STEPS_PER_EIGHTH * TICKS_PER_STEP;
  for (size_t i = 0; i < genre.melody.size(); ++i) {
    if (genre.melody[i] < 0) continue;
    int note = scaleNote(leadRoot, genre.scale, chordDegree + genre.melody[i]);
    midi.addNote(track, barTick + static_cast<int>(i) * eighthTicks,
                 eighthTicks - NOTE_GAP_TICKS, LEAD_CHANNEL, note, velocity);
  }
}

// root + fifth held for the whole bar, fills in the background
void playPad(MidiWriter& midi, int track, int barTick, int chordRoot, int chordFifth,
             int velocity) {
  for (int note : {chordRoot, chordFifth}) {
    midi.addNote(track, barTick, TICKS_PER_BAR - NOTE_GAP_TICKS, PAD_CHANNEL, note, velocity);
  }
}

}  // namespace

std::string composeMidi(const SongPlan& plan) {
  const GenreTemplate& genre = *plan.genre;
  const Patterns& patterns = genre.patterns;

  MidiWriter midi(TICKS_PER_BEAT);
  midi.setTempo(plan.tempoBpm);
  Tracks tracks{midi.addTrack(), midi.addTrack(), midi.addTrack(), midi.addTrack(),
                midi.addTrack()};
  midi.addProgramChange(tracks.bass, 0, BASS_CHANNEL, genre.instruments.bass);
  midi.addProgramChange(tracks.chords, 0, CHORD_CHANNEL, genre.instruments.chords);
  midi.addProgramChange(tracks.lead, 0, LEAD_CHANNEL, genre.instruments.lead);
  midi.addProgramChange(tracks.pad, 0, PAD_CHANNEL, genre.instruments.pad);

  int bar = 0;
  for (size_t s = 0; s < plan.sections.size(); ++s) {
    const Section& section = plan.sections[s];
    bool nextIsLouder = s + 1 < plan.sections.size() && plan.sections[s + 1].energy > section.energy;
    int velocity = velocityFor(section.energy);
    midi.addMarker(tracks.drums, bar * TICKS_PER_BAR, sectionName(section.type));

    for (int barInSection = 0; barInSection < section.bars; ++barInSection, ++bar) {
      int barTick = bar * TICKS_PER_BAR;
      int degree = genre.progression[bar % genre.progression.size()];

      // triad = stack of thirds -> root, +2 steps, +4 steps (in the scale, not semitones)
      int chordRoot = scaleNote(plan.rootNote, genre.scale, degree);
      int chordThird = scaleNote(plan.rootNote, genre.scale, degree + 2);
      int chordFifth = scaleNote(plan.rootNote, genre.scale, degree + 4);

      if (section.energy >= DRUMS_MIN_ENERGY) {
        playDrum(midi, tracks.drums, barTick, patterns.kick, KICK, velocity);
        playDrum(midi, tracks.drums, barTick, patterns.snare, genre.snareSound, velocity);
        playDrum(midi, tracks.drums, barTick, patterns.hat, CLOSED_HAT, velocity - 20);
        if (section.energy >= OPEN_HAT_MIN_ENERGY) {
          playDrum(midi, tracks.drums, barTick, patterns.openHat, OPEN_HAT, velocity - 15);
        }
        if (section.type == SectionType::DROP && barInSection == 0) {
          midi.addNote(tracks.drums, barTick, TICKS_PER_BEAT, DRUM_CHANNEL, CRASH, velocity);
        }
        if (nextIsLouder && barInSection == section.bars - 1) {
          playFill(midi, tracks.drums, barTick, genre.snareSound, velocity);
        }
      }
      if (section.energy >= BASS_MIN_ENERGY) {
        playBass(midi, tracks.bass, barTick, patterns.bass, chordRoot, chordFifth, velocity);
      }
      playChords(midi, tracks.chords, barTick, patterns.chords,
                 {chordRoot, chordThird, chordFifth}, velocity - 10);
      playPad(midi, tracks.pad, barTick, chordRoot, chordFifth, velocity - 25);
      if (section.energy >= LEAD_MIN_ENERGY) {
        playLead(midi, tracks.lead, barTick, plan, degree, velocity);
      }
    }
  }
  return midi.toBytes();
}
