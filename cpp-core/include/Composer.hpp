// SongPlan to a 5-track MIDI file (drums, bass, chords, lead, pad), returned as raw .mid bytes.
// Called from HttpServer.cpp /compose after SongPlanner.cpp has made the plan. Uses
// MidiWriter.cpp for the file format and MusicTheory.hpp for ticks and GM numbers.
#pragma once

#include <string>

#include "SongPlanner.hpp"

// The returned string holds binary bytes, not text; HttpServer.cpp sends it as audio/midi and
// audio-producer/render.py renders it.
std::string composeMidi(const SongPlan& plan);
