// genre + features -> the actual plan (tempo, key, sections w/ energy).
// no notes yet, that's Composer's job
#pragma once

#include <vector>

#include "GenreTemplate.hpp"
#include "ImageFeatures.hpp"

struct SongPlan {
  const GenreTemplate* genre;
  int tempoBpm;
  int rootNote;                   // midi note # of the key (48-59)
  std::vector<Section> sections;  // copy of the genre's sections w/ drop energy bumped
};

SongPlan planSong(const ImageFeatures& features, Genre genre);
