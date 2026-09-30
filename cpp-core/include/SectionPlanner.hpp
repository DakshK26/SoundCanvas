// Genre plus image features to a SongPlan: tempo, key, and the sections with their energies.
// No notes yet; Composer turns the plan into MIDI.
#pragma once

#include <vector>

#include "GenreTemplate.hpp"
#include "ImageFeatures.hpp"

struct SongPlan {
  const GenreTemplate* genre;
  int tempoBpm;
  int rootNote;  // MIDI note, 48 to 59
  std::vector<Section> sections;
};

SongPlan planSong(const ImageFeatures& features, Genre genre);
