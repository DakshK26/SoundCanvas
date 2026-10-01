// Works out tempo, key and section energies for one song. The genre gives the ranges and the photo
// decides where in them this song lands, so two photos in the same genre still sound different.
// Called from HttpServer.cpp /compose; the plan it returns goes straight to Composer.cpp.
#include "SongPlanner.hpp"

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
  // Red minus blue is between -1 and 1; adding 1 and halving moves it to 0 to 1. The clamp is
  // a guard so the key can never leave the octave.
  float warmth = std::clamp((f.avgRed - f.avgBlue + 1.0f) / 2.0f, 0.0f, 1.0f);
  // 0 to 11 semitones above C3, so all 12 keys are reachable.
  int semitonesUp = static_cast<int>(std::round(warmth * (music::SEMITONES_PER_OCTAVE - 1)));
  return music::LOWEST_ROOT_NOTE + semitonesUp;
}

// Saturation gets the most weight because it affects arousal more than brightness does
// (Valdez and Mehrabian 1994). The exact weights are my own choice.
float imageEnergy(const ImageFeatures& f) {
  // Contrast tops out at 0.5, so doubling it puts it on the same 0 to 1 scale as the others.
  float raw = 0.5f * f.saturation + 0.3f * f.colorfulness + 0.2f * (f.contrast * 2.0f);
  // Squeezed into 0.3 to 0.9, so even a dull photo gives some energy and none gives the maximum.
  return 0.3f + 0.6f * std::clamp(raw, 0.0f, 1.0f);
}

}  // namespace

// Copies the genre's sections, then bumps only the drops using the photo's energy.
SongPlan planSong(const ImageFeatures& features, Genre genre) {
  const GenreTemplate& recipe = templateFor(genre);
  SongPlan plan{&recipe, pickTempo(features, recipe), pickRootNote(features), recipe.sections};

  // Only the drops get louder, so the quiet sections stay quiet and the song keeps its contrast.
  // The boost is at most 0.3 times 0.9, and std::min keeps energy at or below 1.
  float boost = 0.3f * imageEnergy(features);
  for (Section& section : plan.sections) {
    if (section.type == SectionType::DROP) {
      section.energy = std::min(1.0f, section.energy + boost);
    }
  }
  return plan;
}
