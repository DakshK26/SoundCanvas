// plan -> actual midi. 5 tracks: drums, bass, chords, lead, pad
#pragma once

#include <string>

#include "SectionPlanner.hpp"

// returns raw .mid file bytes
std::string composeMidi(const SongPlan& plan);
