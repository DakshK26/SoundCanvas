// Genre templates: the fixed recipe for each of the five genres.
// The ml service picks the genre; this file says what that genre sounds like.
#pragma once

#include <string>
#include <vector>

enum class Genre { EDM_CHILL, EDM_DROP, RETROWAVE, CINEMATIC, HOUSE };

// One part of the song, e.g. an 8-bar "drop" at full energy.
struct Section {
  std::string name;  // intro, build, drop, break, or outro
  int bars;
  float energy;      // 0 (quiet) to 1 (full); decides which parts play
};

// Rhythm patterns, one character per 16th-note step (16 characters per bar).
//   drums:  'x' = hit, '.' = silence
//   bass:   'R' = root, 'F' = fifth, 'O' = octave up, '-' = hold, '.' = silence
//   chords: 'x' = play the chord, '-' = hold, '.' = silence
struct Patterns {
  std::string kick;
  std::string snare;
  std::string hat;
  std::string openHat;
  std::string bass;
  std::string chords;
};

// General MIDI instrument numbers for the four pitched parts.
struct Instruments {
  int bass;
  int chords;
  int lead;
  int pad;
};

struct GenreTemplate {
  Genre genre;
  std::string name;
  int minTempo;                  // beats per minute
  int maxTempo;
  std::vector<int> scale;        // see MusicTheory.hpp
  std::vector<int> progression;  // one chord per bar, repeating
  std::vector<Section> sections;
  Patterns patterns;
  int snareSound;                // which GM drum note plays the snare pattern
  Instruments instruments;
  std::vector<int> melody;       // 8 eighth notes per bar, as scale steps; -1 = rest
};

// Turns "HOUSE" into Genre::HOUSE. Throws on an unknown name.
Genre parseGenre(const std::string& name);

// Returns the template for a genre.
const GenreTemplate& templateFor(Genre genre);
