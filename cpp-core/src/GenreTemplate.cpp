// The five genre recipes. Tempos and drum patterns follow each style's usual conventions, like
// house: a kick on every beat, hats on the off-beats, 120 to 130 bpm.
#include "GenreTemplate.hpp"

#include <stdexcept>

#include "MusicTheory.hpp"

using namespace music;

namespace {

// Each template, in field order: genre, name, tempo range, scale, progression, sections as
// (type, bars, energy), patterns, snare sound, instruments (bass, chords, lead, pad), melody.
constexpr SectionType INTRO = SectionType::INTRO, BUILD = SectionType::BUILD, DROP = SectionType::DROP,
                      BREAK = SectionType::BREAK, OUTRO = SectionType::OUTRO;

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

const GenreTemplate RETROWAVE_TEMPLATE = {
    Genre::RETROWAVE, "RETROWAVE", 90, 110,
    MINOR_SCALE, MINOR_LOOP_PROGRESSION,
    {{INTRO, 4, 0.3f}, {BUILD, 8, 0.5f}, {DROP, 8, 0.8f},
     {BREAK, 8, 0.5f}, {DROP, 8, 0.8f}, {OUTRO, 4, 0.3f}},
    {
        "x.......x.x.....",  // kick
        "....x.......x...",  // snare
        "x.x.x.x.x.x.x.x.",  // hat
        "",                  // open hat
        "R-O-R-O-R-O-R-O-",  // bass
        "x-------x-------",  // chords
    },
    SNARE,
    {SYNTH_BASS, POLYSYNTH_PAD, SAW_LEAD, WARM_PAD},
    {4, -1, 2, 0, -1, 2, 4, 5},
};

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
const char* sectionName(SectionType type) {
  switch (type) {
    case SectionType::INTRO: return "intro";
    case SectionType::BUILD: return "build";
    case SectionType::DROP: return "drop";
    case SectionType::BREAK: return "break";
    case SectionType::OUTRO: return "outro";
  }
  throw std::invalid_argument("Unknown section type");
}

// The genre string from GraphQL and from ml/predict, mapped to the enum.
Genre parseGenre(const std::string& name) {
  if (name == "EDM_CHILL") return Genre::EDM_CHILL;
  if (name == "EDM_DROP") return Genre::EDM_DROP;
  if (name == "RETROWAVE") return Genre::RETROWAVE;
  if (name == "CINEMATIC") return Genre::CINEMATIC;
  if (name == "HOUSE") return Genre::HOUSE;
  throw std::invalid_argument("Unknown genre: " + name);
}

const GenreTemplate& templateFor(Genre genre) {
  switch (genre) {
    case Genre::EDM_CHILL: return EDM_CHILL_TEMPLATE;
    case Genre::EDM_DROP: return EDM_DROP_TEMPLATE;
    case Genre::RETROWAVE: return RETROWAVE_TEMPLATE;
    case Genre::CINEMATIC: return CINEMATIC_TEMPLATE;
    case Genre::HOUSE: return HOUSE_TEMPLATE;
  }
  throw std::invalid_argument("Unknown genre");
}
