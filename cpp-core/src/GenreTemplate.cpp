// The five genre recipes. Tempo ranges and drum patterns follow the usual
// conventions of each style (for example, House is "four on the floor":
// a kick on every beat at 120-130 BPM).
#include "GenreTemplate.hpp"

#include <stdexcept>

#include "MusicTheory.hpp"

using namespace music;

namespace {

const GenreTemplate EDM_CHILL_TEMPLATE = {
    Genre::EDM_CHILL, "EDM_CHILL", 100, 115,
    MAJOR_SCALE, POP_PROGRESSION,
    {{"intro", 4, 0.2f}, {"build", 8, 0.5f}, {"drop", 8, 0.7f},
     {"break", 4, 0.4f}, {"drop", 8, 0.7f}, {"outro", 4, 0.2f}},
    {
        "x.......x.......",  // kick: beats 1 and 3, laid back
        "....x.......x...",  // snare: beats 2 and 4
        "x...x...x...x...",  // hats: on the beat
        "",                  // no open hats
        "R-------F-------",  // bass: long root and fifth
        "x---------------",  // chords: one long chord per bar
    },
    SNARE,
    {SYNTH_BASS, ELECTRIC_PIANO, SQUARE_LEAD, WARM_PAD},
    {0, -1, 2, -1, 4, -1, 2, -1},
};

const GenreTemplate EDM_DROP_TEMPLATE = {
    Genre::EDM_DROP, "EDM_DROP", 125, 135,
    MINOR_SCALE, EPIC_MINOR_PROGRESSION,
    {{"intro", 4, 0.3f}, {"build", 8, 0.6f}, {"drop", 8, 1.0f},
     {"build", 4, 0.7f}, {"drop", 8, 1.0f}, {"outro", 4, 0.3f}},
    {
        "x...x...x...x...",  // kick: every beat
        "....x.......x...",  // snare: beats 2 and 4
        "x.x.x.x.x.x.x.x.",  // hats: every 8th note
        "..............x.",  // open hat leading into the next bar
        "R-R-R-R-F-F-O-O-",  // bass: driving 8th notes
        "x--x--x---x--x--",  // chords: syncopated stabs (3 + 3 + 4 + 3 + 3)
    },
    SNARE,
    {SYNTH_BASS, SAW_LEAD, SAW_LEAD, POLYSYNTH_PAD},
    {0, 0, 2, 4, 4, 2, 4, 5},
};

const GenreTemplate RETROWAVE_TEMPLATE = {
    Genre::RETROWAVE, "RETROWAVE", 90, 110,
    MINOR_SCALE, MINOR_LOOP_PROGRESSION,
    {{"intro", 4, 0.3f}, {"build", 8, 0.5f}, {"drop", 8, 0.8f},
     {"break", 8, 0.5f}, {"drop", 8, 0.8f}, {"outro", 4, 0.3f}},
    {
        "x.......x.x.....",  // kick: 80s rock-style beat
        "....x.......x...",  // snare: beats 2 and 4 (the classic gated snare slot)
        "x.x.x.x.x.x.x.x.",  // hats: every 8th note
        "",
        "R-O-R-O-R-O-R-O-",  // bass: octave-jumping 8th notes, the synthwave signature
        "x-------x-------",  // chords: two long chords per bar
    },
    SNARE,
    {SYNTH_BASS, POLYSYNTH_PAD, SAW_LEAD, WARM_PAD},
    {4, -1, 2, 0, -1, 2, 4, 5},
};

const GenreTemplate CINEMATIC_TEMPLATE = {
    Genre::CINEMATIC, "CINEMATIC", 70, 90,
    MINOR_SCALE, EPIC_MINOR_PROGRESSION,
    {{"intro", 8, 0.2f}, {"build", 12, 0.5f}, {"drop", 8, 0.9f},
     {"break", 8, 0.4f}, {"outro", 8, 0.2f}},
    {
        "x...............",  // kick: one deep hit per bar
        "......x.......x.",  // toms: timpani-style hits
        "",                  // no hats
        "",
        "R---------------",  // bass: one sustained note per bar
        "x---------------",  // chords: sustained strings
    },
    LOW_TOM,
    {FINGERED_BASS, STRINGS, SYNTH_BRASS, CHOIR_PAD},
    {0, -1, -1, -1, 2, -1, 4, -1},
};

const GenreTemplate HOUSE_TEMPLATE = {
    Genre::HOUSE, "HOUSE", 120, 130,
    DORIAN_SCALE, ANTHEM_PROGRESSION,
    {{"intro", 8, 0.3f}, {"build", 8, 0.6f}, {"drop", 16, 0.9f},
     {"break", 8, 0.4f}, {"drop", 16, 1.0f}, {"outro", 8, 0.3f}},
    {
        "x...x...x...x...",  // kick: four on the floor
        "....x.......x...",  // clap: beats 2 and 4
        "..x...x...x...x.",  // hats: on the off-beats, the house signature
        "..............x.",  // open hat leading into the next bar
        "..R-..R-..R-..O-",  // bass: off-beat notes between the kicks
        "..x-..x-..x-..x-",  // chords: off-beat piano stabs
    },
    CLAP,
    {SYNTH_BASS, ACOUSTIC_PIANO, SQUARE_LEAD, WARM_PAD},
    {0, -1, 2, -1, 4, 2, -1, 0},
};

}  // namespace

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
