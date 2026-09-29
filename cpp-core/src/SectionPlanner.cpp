#include "SectionPlanner.hpp"

#include <algorithm>
#include <cmath>

#include "MusicTheory.hpp"

namespace {

int pickTempo(const ImageFeatures& f, const GenreTemplate& genre) {
  float range = static_cast<float>(genre.maxTempo - genre.minTempo);
  return genre.minTempo + static_cast<int>(std::round(f.brightness * range));
}

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

  float boost = 0.3f * imageEnergy(features);
  for (Section& section : plan.sections) {
    if (section.type == SectionType::DROP) {
      section.energy = std::min(1.0f, section.energy + boost);
    }
  }
  return plan;
}
