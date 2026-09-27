// Song planning: the image decides where inside the genre's ranges the song lands.
#include "SectionPlanner.hpp"

#include <algorithm>
#include <cmath>

#include "MusicTheory.hpp"

namespace {

// Brighter images play faster, within the genre's tempo range.
int pickTempo(const ImageFeatures& f, const GenreTemplate& genre) {
  float range = static_cast<float>(genre.maxTempo - genre.minTempo);
  return genre.minTempo + static_cast<int>(std::round(f.brightness * range));
}

// Warmer images (more red than blue) get a higher key, from C3 up to B3.
int pickRootNote(const ImageFeatures& f) {
  float warmth = std::clamp((f.avgRed - f.avgBlue + 1.0f) / 2.0f, 0.0f, 1.0f);
  int semitonesUp = static_cast<int>(std::round(warmth * (music::SEMITONES_PER_OCTAVE - 1)));
  return music::LOWEST_ROOT_NOTE + semitonesUp;
}

// How energetic the image feels, 0.3 to 0.9. Saturation weighs most: in colour-emotion
// studies it drives arousal more than brightness does (Valdez & Mehrabian, 1994).
float imageEnergy(const ImageFeatures& f) {
  // Contrast only reaches 0.5, so double it to put it on the same 0-1 scale.
  float raw = 0.5f * f.saturation + 0.3f * f.colorfulness + 0.2f * (f.contrast * 2.0f);
  return 0.3f + 0.6f * std::clamp(raw, 0.0f, 1.0f);
}

}  // namespace

SongPlan planSong(const ImageFeatures& features, Genre genre) {
  const GenreTemplate& recipe = templateFor(genre);
  SongPlan plan{&recipe, pickTempo(features, recipe), pickRootNote(features), recipe.sections};

  // Energetic images hit harder in the drops.
  float boost = 0.3f * imageEnergy(features);
  for (Section& section : plan.sections) {
    if (section.type == SectionType::DROP) {
      section.energy = std::min(1.0f, section.energy + boost);
    }
  }
  return plan;
}
