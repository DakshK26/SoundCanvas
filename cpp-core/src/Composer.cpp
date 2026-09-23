// The composer walks the song bar by bar. For each bar it picks the current
// chord from the genre's progression and plays each part's 16-step pattern.
// A section's energy decides which parts join in, so intros stay sparse and
// drops play everything.
#include "Composer.hpp"

#include <vector>

#include "MidiWriter.hpp"
#include "MusicTheory.hpp"

using namespace music;

namespace {

// Which parts play, by section energy (0 to 1).
constexpr float BASS_MIN_ENERGY = 0.3f;      // intros may drop the bass
constexpr float DRUMS_MIN_ENERGY = 0.4f;     // intros and outros drop the beat
constexpr float LEAD_MIN_ENERGY = 0.7f;      // the melody is saved for the drops
constexpr float OPEN_HAT_MIN_ENERGY = 0.8f;  // extra sizzle only at full energy

// Each pitched part gets its own MIDI channel so it can have its own instrument.
constexpr int BASS_CHANNEL = 0;
constexpr int CHORD_CHANNEL = 1;
constexpr int LEAD_CHANNEL = 2;
constexpr int PAD_CHANNEL = 3;

// A few ticks of silence at the end of each note, so repeated notes re-trigger.
constexpr int NOTE_GAP_TICKS = 10;

// Eighth notes for the lead melody: two 16th-note steps each.
constexpr int STEPS_PER_EIGHTH = 2;

struct Tracks {
  int drums, bass, chords, lead, pad;
};

// MIDI velocity (1-127 loudness) grows with section energy.
int velocityFor(float energy) { return 50 + static_cast<int>(energy * 60.0f); }

// The note `degree` steps up the scale from the root, wrapping into higher octaves.
int scaleNote(int root, const std::vector<int>& scale, int degree) {
  int size = static_cast<int>(scale.size());
  return root + (degree / size) * SEMITONES_PER_OCTAVE + scale[degree % size];
}

// Calls play(startStep, lengthInSteps, symbol) for every note in a 16-step pattern.
// A note lasts through any '-' characters that follow it.
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

// Plays one drum sound wherever its pattern has an 'x'.
void playDrum(MidiWriter& midi, int track, int barTick, const std::string& pattern, int drum,
              int velocity) {
  forEachNote(pattern, [&](int step, int, char) {
    midi.addNote(track, barTick + step * TICKS_PER_STEP, TICKS_PER_STEP, DRUM_CHANNEL, drum,
                 velocity);
  });
}

// A snare roll over the last beat of a bar, leading into a louder section.
void playFill(MidiWriter& midi, int track, int barTick, int snare, int velocity) {
  for (int step = STEPS_PER_BAR - 4; step < STEPS_PER_BAR; ++step) {
    midi.addNote(track, barTick + step * TICKS_PER_STEP, TICKS_PER_STEP, DRUM_CHANNEL, snare,
                 velocity);
  }
}

// Plays the bass pattern. 'R' = chord root, 'F' = its fifth, 'O' = root an octave up.
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

// Plays every note of the chord wherever the chord pattern has an 'x'.
void playChords(MidiWriter& midi, int track, int barTick, const std::string& pattern,
                const std::vector<int>& chord, int velocity) {
  forEachNote(pattern, [&](int step, int length, char) {
    for (int note : chord) {
      midi.addNote(track, barTick + step * TICKS_PER_STEP,
                   length * TICKS_PER_STEP - NOTE_GAP_TICKS, CHORD_CHANNEL, note, velocity);
    }
  });
}

// Plays the genre's 8-note melody one octave above the chord. -1 is a rest.
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

// Holds the chord's root and fifth under everything for the whole bar.
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
    midi.addMarker(tracks.drums, bar * TICKS_PER_BAR, section.name);

    for (int barInSection = 0; barInSection < section.bars; ++barInSection, ++bar) {
      int barTick = bar * TICKS_PER_BAR;
      int degree = genre.progression[bar % genre.progression.size()];

      // A triad: the chord's root plus the notes 2 and 4 scale steps above it.
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
        if (section.name == "drop" && barInSection == 0) {
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
