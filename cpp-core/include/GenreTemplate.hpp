// What each genre sounds like: tempo range, scale, chords, sections, patterns and instruments.
// The model only picks the genre; this decides how that genre is played. The four recipes are
// in GenreTemplate.cpp; SongPlanner.cpp and Composer.cpp read them.
#pragma once

#include <string>
#include <vector>

// The four genres the model in ml/ can predict. The names must match ml/genres.py.
enum class Genre { EDM_CHILL, EDM_DROP, CINEMATIC, HOUSE };

// The kinds of section a song is built from, in the order a template lists them.
enum class SectionType { INTRO, BUILD, DROP, BREAK, OUTRO };

// Written into the MIDI as markers; audio-producer/fx.py looks for "drop" and "break".
const char* sectionName(SectionType type);

// One block of the song, like an 8-bar drop.
struct Section {
  SectionType type;  // which kind of block, also the marker text
  int bars;          // length in 4/4 bars
  float energy;      // 0 to 1; Composer.cpp uses it for which parts play and how hard
};

// One character per 16th step, 16 per bar.
//   drums:  x = hit, . = nothing
//   bass:   R = root, F = fifth, O = octave up, - = hold, . = nothing
//   chords: x = play, - = hold, . = nothing
// An empty string means that part never plays in this genre.
struct Patterns {
  std::string kick;     // kick drum
  std::string snare;    // played with GenreTemplate::snareSound
  std::string hat;      // closed hi-hat
  std::string openHat;  // open hi-hat, only in the loudest sections
  std::string bass;     // bass line, using R, F and O
  std::string chords;   // when the triad is struck and how long it is held
};

// GM program numbers.
struct Instruments {
  int bass;    // bass track
  int chords;  // chord track
  int lead;    // melody track
  int pad;     // held background track
};

// One full genre recipe. GenreTemplate.cpp fills these in field order.
struct GenreTemplate {
  // Identity
  Genre genre;
  std::string name;  // same text as the enum, used by parseGenre and the tests

  // Tempo and harmony
  int minTempo;  // bpm, used for brightness 0
  int maxTempo;  // bpm, used for brightness 1
  std::vector<int> scale;        // semitone offsets from MusicTheory.hpp
  std::vector<int> progression;  // one chord per bar

  // Arrangement and sound
  std::vector<Section> sections;
  Patterns patterns;
  int snareSound;  // the snare pattern can play a clap or a tom
  Instruments instruments;
  std::vector<int> melody;  // 8 eighth notes per bar as scale steps, -1 is a rest
};

// Throws for an unknown name.
Genre parseGenre(const std::string& name);

// The recipe for a genre. The reference stays valid for the whole program.
const GenreTemplate& templateFor(Genre genre);
