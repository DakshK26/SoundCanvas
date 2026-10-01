// Genre plus image features to a SongPlan: tempo, key, and the sections with their energies.
// No notes yet; Composer turns the plan into MIDI. Called from HttpServer.cpp /compose, and it
// reads the genre's ranges from GenreTemplate.cpp.
#pragma once

#include <vector>

#include "GenreTemplate.hpp"
#include "ImageFeatures.hpp"

// Everything Composer.cpp needs to write the song.
struct SongPlan {
  const GenreTemplate* genre;     // points at one of the static templates, so it never dangles
  int tempoBpm;                   // within the genre's minTempo to maxTempo
  int rootNote;                   // MIDI note, 48 to 59
  std::vector<Section> sections;  // the genre's sections, with the drops boosted by the photo
};

// Pure function: the same features and genre always give the same plan.
SongPlan planSong(const ImageFeatures& features, Genre genre);
