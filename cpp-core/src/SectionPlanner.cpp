// Works out tempo, key and section energies for one song. The genre gives the ranges and the photo
// decides where in them this song lands, so two photos in the same genre still sound different.
#include "SectionPlanner.hpp"

#include <algorithm>
#include <cmath>

#include "MusicTheory.hpp"

namespace {

// Brighter is faster: brightness 0 gives the genre's slowest tempo, 1 its fastest.
int pickTempo(const ImageFeatures& f, const GenreTemplate& genre) {
  float range = static_cast<float>(genre.maxTempo - genre.minTempo);
  return genre.minTempo + static_cast<int>(std::round(f.brightness * range));
}

// Warmer photos (more red than blue) get a higher key, from C3 up to B3.
int pickRootNote(const ImageFeatures& f) {
  float warmth = std::clamp((f.avgRed - f.avgBlue + 1.0f) / 2.0f, 0.0f, 1.0f);
  int semitonesUp = static_cast<int>(std::round(warmth * (music::SEMITONES_PER_OCTAVE - 1)));
  return music::LOWEST_ROOT_NOTE + semitonesUp;
}

// Saturation gets the most weight because it affects arousal more than brightness does
// (Valdez and Mehrabian 1994). The exact weights are my own choice.
float imageEnergy(const ImageFeatures& f) {
  float raw = 0.5f * f.saturation + 0.3f * f.colorfulness + 0.2f * (f.contrast * 2.0f);
  return 0.3f + 0.6f * std::clamp(raw, 0.0f, 1.0f);
}

}  // namespace

SongPlan planSong(const ImageFeatures& features, Genre genre) {
  const GenreTemplate& recipe = templateFor(genre);
  SongPlan plan{&recipe, pickTempo(features, recipe), pickRootNote(features), recipe.sections};

  // Only the drops get louder, so the quiet sections stay quiet and the song keeps its contrast.
  float boost = 0.3f * imageEnergy(features);
  for (Section& section : plan.sections) {
    if (section.type == SectionType::DROP) {
      section.energy = std::min(1.0f, section.energy + boost);
    }
  }
  return plan;
}
