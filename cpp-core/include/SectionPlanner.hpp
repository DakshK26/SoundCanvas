// Turns a genre and an image's features into a concrete song plan:
// tempo, key, and the list of sections with their energy levels.
#pragma once

#include <vector>

#include "GenreTemplate.hpp"
#include "ImageFeatures.hpp"

struct SongPlan {
  const GenreTemplate* genre;
  int tempoBpm;
  int rootNote;                   // MIDI note number of the key's root
  std::vector<Section> sections;  // the genre's sections, adjusted for this image
};

SongPlan planSong(const ImageFeatures& features, Genre genre);
