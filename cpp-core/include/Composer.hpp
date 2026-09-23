// Writes the song plan out as a multi-track MIDI file:
// drums, bass, chords, lead melody, and a background pad.
#pragma once

#include <string>

#include "SectionPlanner.hpp"

// Returns the bytes of a .mid file for the whole song.
std::string composeMidi(const SongPlan& plan);
