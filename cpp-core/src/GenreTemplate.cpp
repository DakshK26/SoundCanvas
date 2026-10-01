// The genre recipes. Tempos and drum patterns follow each style's usual conventions, like
// house: a kick on every beat, hats on the off-beats, 120 to 130 bpm.
// SongPlanner.cpp reads the tempo range and sections, Composer.cpp the rest. The genre names must
// match ml/genres.py, KITS in audio-producer/drums.py and MIXES in audio-producer/mixer.py.
#include "GenreTemplate.hpp"

#include <stdexcept>

#include "MusicTheory.hpp"

using namespace music;

namespace {

// Each template, in field order: genre, name, tempo range, scale, progression, sections as
// (type, bars, energy), patterns, snare sound, instruments (bass, chords, lead, pad), melody.
// Read top to bottom, that is: the tempo line, the harmony line, the sections in playing order,
// the six 16-step patterns labelled on the right, then sound, instruments and melody. The melody
// is scale steps above the current chord, one per eighth note.
// Short names so the section lists below fit on one line.
constexpr SectionType INTRO = SectionType::INTRO, BUILD = SectionType::BUILD, DROP = SectionType::DROP,
                      BREAK = SectionType::BREAK, OUTRO = SectionType::OUTRO;

// Relaxed and bright: major key, kick on beats 1 and 3, one held chord per bar, no open hat.
const GenreTemplate EDM_CHILL_TEMPLATE = {
    Genre::EDM_CHILL, "EDM_CHILL", 100, 115,
    MAJOR_SCALE, POP_PROGRESSION,
    {{INTRO, 4, 0.2f}, {BUILD, 8, 0.5f}, {DROP, 8, 0.7f},
     {BREAK, 4, 0.4f}, {DROP, 8, 0.7f}, {OUTRO, 4, 0.2f}},
    {
        "x.......x.......",  // kick
        "....x.......x...",  // snare
        "x...x...x...x...",  // hat
        "",                  // open hat
        "R-------F-------",  // bass
        "x---------------",  // chords
    },
    SNARE,
    {SYNTH_BASS, ELECTRIC_PIANO, SQUARE_LEAD, WARM_PAD},
    {0, -1, 2, -1, 4, -1, 2, -1},
};

// Big and dark: minor key, four-on-the-floor kick, 8th-note hats, a busy bass and syncopated
// chords. Both drops are at full energy, with a second build instead of a break between them.
const GenreTemplate EDM_DROP_TEMPLATE = {
    Genre::EDM_DROP, "EDM_DROP", 125, 135,
    MINOR_SCALE, EPIC_MINOR_PROGRESSION,
    {{INTRO, 4, 0.3f}, {BUILD, 8, 0.6f}, {DROP, 8, 1.0f},
     {BUILD, 4, 0.7f}, {DROP, 8, 1.0f}, {OUTRO, 4, 0.3f}},
    {
        "x...x...x...x...",  // kick
        "....x.......x...",  // snare
        "x.x.x.x.x.x.x.x.",  // hat
        "..............x.",  // open hat
        "R-R-R-R-F-F-O-O-",  // bass
        "x--x--x---x--x--",  // chords
    },
    SNARE,
    {SYNTH_BASS, SAW_LEAD, SAW_LEAD, POLYSYNTH_PAD},
    {0, 0, 2, 4, 4, 2, 4, 5},
};

// Slow and sparse: one kick per bar, a low tom instead of a snare, no hats, orchestral sounds.
// Longer sections and a single drop.
const GenreTemplate CINEMATIC_TEMPLATE = {
    Genre::CINEMATIC, "CINEMATIC", 70, 90,
    MINOR_SCALE, EPIC_MINOR_PROGRESSION,
    {{INTRO, 8, 0.2f}, {BUILD, 12, 0.5f}, {DROP, 8, 0.9f},
     {BREAK, 8, 0.4f}, {OUTRO, 8, 0.2f}},
    {
        "x...............",  // kick
        "......x.......x.",  // snare
        "",                  // hat
        "",                  // open hat
        "R---------------",  // bass
        "x---------------",  // chords
    },
    LOW_TOM,
    {FINGERED_BASS, STRINGS, SYNTH_BRASS, CHOIR_PAD},
    {0, -1, -1, -1, 2, -1, 4, -1},
};

// Kick on every beat, clap on 2 and 4, hats and bass on the off-beats, piano stabs.
// Dorian is a minor scale with a brighter 6th. The drops are 16 bars, twice the other genres'.
const GenreTemplate HOUSE_TEMPLATE = {
    Genre::HOUSE, "HOUSE", 120, 130,
    DORIAN_SCALE, ANTHEM_PROGRESSION,
    {{INTRO, 8, 0.3f}, {BUILD, 8, 0.6f}, {DROP, 16, 0.9f},
     {BREAK, 8, 0.4f}, {DROP, 16, 1.0f}, {OUTRO, 8, 0.3f}},
    {
        "x...x...x...x...",  // kick
        "....x.......x...",  // snare
        "..x...x...x...x.",  // hat
        "..............x.",  // open hat
        "..R-..R-..R-..O-",  // bass
        "..x-..x-..x-..x-",  // chords
    },
    CLAP,
    {SYNTH_BASS, ACOUSTIC_PIANO, SQUARE_LEAD, WARM_PAD},
    {0, -1, 2, -1, 4, 2, -1, 0},
};

}  // namespace

// These lowercase names are what audio-producer sees in the MIDI markers.
// audio-producer/fx.py compares against "drop" and "break", so those two must not change.
const char* sectionName(SectionType type) {
  switch (type) {
    case SectionType::INTRO: return "intro";
    case SectionType::BUILD: return "build";
    case SectionType::DROP: return "drop";
    case SectionType::BREAK: return "break";
    case SectionType::OUTRO: return "outro";
  }
  // Only reached if the enum holds a value outside the five cases.
  throw std::invalid_argument("Unknown section type");
}

// The genre string from GraphQL and from ml/predict, mapped to the enum.
// An unknown name throws invalid_argument, which HttpServer.cpp turns into a 400.
Genre parseGenre(const std::string& name) {
  if (name == "EDM_CHILL") return Genre::EDM_CHILL;
  if (name == "EDM_DROP") return Genre::EDM_DROP;
  if (name == "CINEMATIC") return Genre::CINEMATIC;
  if (name == "HOUSE") return Genre::HOUSE;
  throw std::invalid_argument("Unknown genre: " + name);
}

// Returns a reference to a static template, so callers can keep the pointer (SongPlan does).
const GenreTemplate& templateFor(Genre genre) {
  switch (genre) {
    case Genre::EDM_CHILL: return EDM_CHILL_TEMPLATE;
    case Genre::EDM_DROP: return EDM_DROP_TEMPLATE;
    case Genre::CINEMATIC: return CINEMATIC_TEMPLATE;
    case Genre::HOUSE: return HOUSE_TEMPLATE;
  }
  throw std::invalid_argument("Unknown genre");
}
