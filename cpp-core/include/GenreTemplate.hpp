// genre "recipes". ml picks WHICH genre, this is what each one actually sounds like
// (tempo range, scale, chords, drum patterns, instruments...)
#pragma once

#include <string>
#include <vector>

enum class Genre { EDM_CHILL, EDM_DROP, RETROWAVE, CINEMATIC, HOUSE };

enum class SectionType { INTRO, BUILD, DROP, BREAK, OUTRO };

// "drop", "intro" etc. goes into the midi as a marker -> audio-producer reads these
// to know where sections start (for risers/fx). don't rename w/o changing the python side
const char* sectionName(SectionType type);

// a chunk of the song, like 8 bars of drop at energy 1.0
struct Section {
  SectionType type;
  int bars;
  float energy;  // 0 quiet .. 1 full. higher = more parts come in
};

// patterns as strings, 1 char = 1 16th step, 16 chars = 1 bar. (way easier to read/edit than arrays)
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

// GM program numbers for the 4 non-drum parts
struct Instruments {
  int bass;
  int chords;
  int lead;
  int pad;
};

struct GenreTemplate {
  Genre genre;
  std::string name;
  int minTempo;                  // bpm. brightness picks where in the range
  int maxTempo;
  std::vector<int> scale;        // from MusicTheory.hpp
  std::vector<int> progression;  // 1 chord/bar, loops
  std::vector<Section> sections;
  Patterns patterns;
  int snareSound;                // snare pattern doesn't have to be a snare (clap for house, tom for cinematic)
  Instruments instruments;
  std::vector<int> melody;       // 8 8th-notes per bar as scale steps, -1 = rest
};

// "HOUSE" -> Genre::HOUSE, throws if unknown
Genre parseGenre(const std::string& name);

const GenreTemplate& templateFor(Genre genre);
