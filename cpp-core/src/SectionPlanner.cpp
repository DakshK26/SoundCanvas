// genre gives the ranges, the image decides where in those ranges this song lands.
// (so 2 HOUSE photos still come out different)
#include "SectionPlanner.hpp"

#include <algorithm>
#include <cmath>

#include "MusicTheory.hpp"

namespace {

// brighter -> faster (brightness 0 = minTempo, 1 = maxTempo)
int pickTempo(const ImageFeatures& f, const GenreTemplate& genre) {
  float range = static_cast<float>(genre.maxTempo - genre.minTempo);
  return genre.minTempo + static_cast<int>(std::round(f.brightness * range));
}

// warm (red > blue) -> higher key, C3..B3. red-blue is -1..1 so shift it to 0..1 first
int pickRootNote(const ImageFeatures& f) {
  float warmth = std::clamp((f.avgRed - f.avgBlue + 1.0f) / 2.0f, 0.0f, 1.0f);
  int semitonesUp = static_cast<int>(std::round(warmth * (music::SEMITONES_PER_OCTAVE - 1)));
  return music::LOWEST_ROOT_NOTE + semitonesUp;
}

// how "energetic" the pic is, 0.3..0.9.
// saturation gets the biggest weight - Valdez & Mehrabian 1994 found saturation affects
// arousal way more than brightness does. weights themselves are my guess
float imageEnergy(const ImageFeatures& f) {
  // contrast maxes at .5 -> x2 so it's 0..1 like the others
  float raw = 0.5f * f.saturation + 0.3f * f.colorfulness + 0.2f * (f.contrast * 2.0f);
  return 0.3f + 0.6f * std::clamp(raw, 0.0f, 1.0f);
}

}  // namespace

SongPlan planSong(const ImageFeatures& features, Genre genre) {
  const GenreTemplate& recipe = templateFor(genre);
  SongPlan plan{&recipe, pickTempo(features, recipe), pickRootNote(features), recipe.sections};

  // only boost the drops, intros/breaks stay the same so there's still contrast
  float boost = 0.3f * imageEnergy(features);
  for (Section& section : plan.sections) {
    if (section.type == SectionType::DROP) {
      section.energy = std::min(1.0f, section.energy + boost);
    }
  }
  return plan;
}
