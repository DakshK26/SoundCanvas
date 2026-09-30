// SongPlan to a 5-track MIDI file (drums, bass, chords, lead, pad), returned as raw .mid bytes.
#pragma once

#include <string>

#include "SectionPlanner.hpp"

std::string composeMidi(const SongPlan& plan);
