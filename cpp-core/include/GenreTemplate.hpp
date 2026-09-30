// What each genre sounds like: tempo range, scale, chords, sections, patterns and instruments.
// The model only picks the genre; this decides how that genre is played.
#pragma once

#include <string>
#include <vector>

enum class Genre { EDM_CHILL, EDM_DROP, RETROWAVE, CINEMATIC, HOUSE };

enum class SectionType { INTRO, BUILD, DROP, BREAK, OUTRO };

// Written into the MIDI as markers; audio-producer/fx.py looks for "drop" and "break".
const char* sectionName(SectionType type);

struct Section {
  SectionType type;
  int bars;
  float energy;  // 0 to 1
};

// One character per 16th step, 16 per bar.
//   drums:  x = hit, . = nothing
//   bass:   R = root, F = fifth, O = octave up, - = hold, . = nothing
//   chords: x = play, - = hold, . = nothing
struct Patterns {
  std::string kick;
  std::string snare;
  std::string hat;
  std::string openHat;
  std::string bass;
  std::string chords;
};

// GM program numbers.
struct Instruments {
  int bass;
  int chords;
  int lead;
  int pad;
};

struct GenreTemplate {
  Genre genre;
  std::string name;
  int minTempo;  // bpm
  int maxTempo;
  std::vector<int> scale;
  std::vector<int> progression;  // one chord per bar
  std::vector<Section> sections;
  Patterns patterns;
  int snareSound;  // the snare pattern can play a clap or a tom
  Instruments instruments;
  std::vector<int> melody;  // 8 eighth notes per bar as scale steps, -1 is a rest
};

// Throws for an unknown name.
Genre parseGenre(const std::string& name);

const GenreTemplate& templateFor(Genre genre);
