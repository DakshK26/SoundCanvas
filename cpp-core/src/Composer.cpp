// Turns a SongPlan into MIDI. Walks the song bar by bar, takes that bar's chord from the
// progression, and plays each part's 16-step pattern over it. Section energy decides which
// parts play, so an intro is mostly chords and pad and a drop has everything.
// Called from HttpServer.cpp /compose with the plan from SongPlanner.cpp. Writes through
// MidiWriter.cpp; audio-producer/app.py renders the result.
#include "Composer.hpp"

#include <vector>

#include "MidiWriter.hpp"
#include "MusicTheory.hpp"

using namespace music;

namespace {

// A part plays when the section's energy is at least this.
constexpr float BASS_MIN_ENERGY = 0.3f;
constexpr float DRUMS_MIN_ENERGY = 0.4f;
constexpr float LEAD_MIN_ENERGY = 0.7f;
constexpr float OPEN_HAT_MIN_ENERGY = 0.8f;

// One channel per part, because a program change applies to the whole channel.
// The drums use DRUM_CHANNEL (9) from MusicTheory.hpp, so 0 to 3 don't clash with it.
constexpr int BASS_CHANNEL = 0;
constexpr int CHORD_CHANNEL = 1;
constexpr int LEAD_CHANNEL = 2;
constexpr int PAD_CHANNEL = 3;

// Without the gap, the same note twice in a row sounds like one long note.
constexpr int NOTE_GAP_TICKS = 10;

constexpr int STEPS_PER_EIGHTH = 2;

// The track index MidiWriter returned for each part.
struct Tracks {
  int drums, bass, chords, lead, pad;
};

// Louder sections hit harder: velocity 50 at energy 0, up to 110 at energy 1.
int velocityFor(float energy) { return 50 + static_cast<int>(energy * 60.0f); }

// Scale degree to MIDI note. Degrees past the end of the scale go up an octave, so degree 7
// in a 7-note scale is the root one octave higher.
// degree / size is how many octaves up; degree % size is the position inside the scale.
int scaleNote(int root, const std::vector<int>& scale, int degree) {
  int size = static_cast<int>(scale.size());
  return root + (degree / size) * SEMITONES_PER_OCTAVE + scale[degree % size];
}

// Calls play(startStep, lengthInSteps, symbol) for each note in the pattern. Every play*
// function below goes through this, so the pattern parsing lives in one place.
template <typename PlayFn>
void forEachNote(const std::string& pattern, PlayFn play) {
  for (int step = 0; step < static_cast<int>(pattern.size()); ++step) {
    char symbol = pattern[step];
    // Rests and holds never start a note; holds are counted by the loop below.
    if (symbol == '.' || symbol == '-') continue;
    // Each '-' right after a note makes it one step longer.
    int length = 1;
    while (step + length < static_cast<int>(pattern.size()) && pattern[step + length] == '-') {
      ++length;
    }
    play(step, length, symbol);
  }
}

// One drum sound, one hit per 'x'. Hats use this too, with a quieter velocity.
// Drum hits are one step long. audio-producer/app.py only reads when each hit starts, and
// audio-producer/drums.py decides how long it rings.
void playDrum(MidiWriter& midi, int track, int barTick, const std::string& pattern, int drum,
              int velocity) {
  forEachNote(pattern, [&](int step, int, char) {
    midi.addNote(track, barTick + step * TICKS_PER_STEP, TICKS_PER_STEP, DRUM_CHANNEL, drum,
                 velocity);
  });
}

// A snare roll on the last beat of the bar, played just before a louder section.
// Steps 12 to 15 are the four 16ths of beat 4.
void playFill(MidiWriter& midi, int track, int barTick, int snare, int velocity) {
  for (int step = STEPS_PER_BAR - 4; step < STEPS_PER_BAR; ++step) {
    midi.addNote(track, barTick + step * TICKS_PER_STEP, TICKS_PER_STEP, DRUM_CHANNEL, snare,
                 velocity);
  }
}

// The bass sits an octave below the chord; 'O' jumps back up to the chord's own octave.
void playBass(MidiWriter& midi, int track, int barTick, const std::string& pattern,
              int chordRoot, int chordFifth, int velocity) {
  int bassRoot = chordRoot - SEMITONES_PER_OCTAVE;
  forEachNote(pattern, [&](int step, int length, char symbol) {
    // 'F' is the fifth, 'O' the octave, and anything else ('R') the root.
    int note = symbol == 'F' ? chordFifth - SEMITONES_PER_OCTAVE
             : symbol == 'O' ? chordRoot
                             : bassRoot;
    midi.addNote(track, barTick + step * TICKS_PER_STEP,
                 length * TICKS_PER_STEP - NOTE_GAP_TICKS, BASS_CHANNEL, note, velocity);
  });
}

// The whole triad on every chord hit.
void playChords(MidiWriter& midi, int track, int barTick, const std::string& pattern,
                const std::vector<int>& chord, int velocity) {
  forEachNote(pattern, [&](int step, int length, char) {
    for (int note : chord) {
      midi.addNote(track, barTick + step * TICKS_PER_STEP,
                   length * TICKS_PER_STEP - NOTE_GAP_TICKS, CHORD_CHANNEL, note, velocity);
    }
  });
}

// The melody is written relative to the current chord, so it follows the progression instead of
// repeating the same notes over every chord. It plays an octave above the key.
void playLead(MidiWriter& midi, int track, int barTick, const SongPlan& plan, int chordDegree,
              int velocity) {
  const GenreTemplate& genre = *plan.genre;
  int leadRoot = plan.rootNote + SEMITONES_PER_OCTAVE;
  int eighthTicks = STEPS_PER_EIGHTH * TICKS_PER_STEP;
  // One melody entry per eighth note; -1 is a rest.
  for (size_t i = 0; i < genre.melody.size(); ++i) {
    if (genre.melody[i] < 0) continue;
    int note = scaleNote(leadRoot, genre.scale, chordDegree + genre.melody[i]);
    midi.addNote(track, barTick + static_cast<int>(i) * eighthTicks,
                 eighthTicks - NOTE_GAP_TICKS, LEAD_CHANNEL, note, velocity);
  }
}

// Root and fifth held for the whole bar, as a background under everything else.
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

  // Setup.
  // One track per part. The drums are track 0, which also carries the tempo and section markers.
  MidiWriter midi(TICKS_PER_BEAT);
  midi.setTempo(plan.tempoBpm);
  Tracks tracks{midi.addTrack(), midi.addTrack(), midi.addTrack(), midi.addTrack(),
                midi.addTrack()};
  // Instruments are set once at tick 0. Drums need no program change; channel 9 is always drums.
  midi.addProgramChange(tracks.bass, 0, BASS_CHANNEL, genre.instruments.bass);
  midi.addProgramChange(tracks.chords, 0, CHORD_CHANNEL, genre.instruments.chords);
  midi.addProgramChange(tracks.lead, 0, LEAD_CHANNEL, genre.instruments.lead);
  midi.addProgramChange(tracks.pad, 0, PAD_CHANNEL, genre.instruments.pad);

  // Per section. bar counts bars across the whole song, so it is not reset between sections.
  int bar = 0;
  for (size_t s = 0; s < plan.sections.size(); ++s) {
    const Section& section = plan.sections[s];
    // Decides whether this section ends with a snare fill into the next one.
    bool nextIsLouder = s + 1 < plan.sections.size() && plan.sections[s + 1].energy > section.energy;
    int velocity = velocityFor(section.energy);
    // audio-producer reads these markers to place its risers and impacts.
    midi.addMarker(tracks.drums, bar * TICKS_PER_BAR, sectionName(section.type));

    // Per bar.
    for (int barInSection = 0; barInSection < section.bars; ++barInSection, ++bar) {
      int barTick = bar * TICKS_PER_BAR;
      // The progression loops, one chord per bar.
      int degree = genre.progression[bar % genre.progression.size()];

      // Offsets are scale steps, not semitones.
      int chordRoot = scaleNote(plan.rootNote, genre.scale, degree);
      int chordThird = scaleNote(plan.rootNote, genre.scale, degree + 2);
      int chordFifth = scaleNote(plan.rootNote, genre.scale, degree + 4);

      // Drums: kick, snare and closed hat, then the extras only louder sections get.
      if (section.energy >= DRUMS_MIN_ENERGY) {
        playDrum(midi, tracks.drums, barTick, patterns.kick, KICK, velocity);
        playDrum(midi, tracks.drums, barTick, patterns.snare, genre.snareSound, velocity);
        playDrum(midi, tracks.drums, barTick, patterns.hat, CLOSED_HAT, velocity - 20);
        if (section.energy >= OPEN_HAT_MIN_ENERGY) {
          playDrum(midi, tracks.drums, barTick, patterns.openHat, OPEN_HAT, velocity - 15);
        }
        // A crash on the first beat of every drop.
        if (section.type == SectionType::DROP && barInSection == 0) {
          midi.addNote(tracks.drums, barTick, TICKS_PER_BEAT, DRUM_CHANNEL, CRASH, velocity);
        }
        // Fills: the snare roll goes in the last bar of a section when the next one is louder.
        if (nextIsLouder && barInSection == section.bars - 1) {
          playFill(midi, tracks.drums, barTick, genre.snareSound, velocity);
        }
      }
      // Bass: from BASS_MIN_ENERGY up.
      if (section.energy >= BASS_MIN_ENERGY) {
        playBass(midi, tracks.bass, barTick, patterns.bass, chordRoot, chordFifth, velocity);
      }
      // Chords and pad: always on, a little quieter so they sit behind the other parts.
      playChords(midi, tracks.chords, barTick, patterns.chords,
                 {chordRoot, chordThird, chordFifth}, velocity - 10);
      playPad(midi, tracks.pad, barTick, chordRoot, chordFifth, velocity - 25);
      // Lead: only in high-energy sections, so the melody arrives with the drops.
      if (section.energy >= LEAD_MIN_ENERGY) {
        playLead(midi, tracks.lead, barTick, plan, degree, velocity);
      }
    }
  }
  return midi.toBytes();
}
