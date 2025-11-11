#pragma once

#include "SongSpec.hpp"
#include "SectionPlanner.hpp"
#include <string>

/**
 * Phase 7: MIDI composition engine
 * Generates complete multi-track MIDI files from SongSpec
 */

/**
 * Compose a complete song to MIDI file based on SongSpec
 * Includes: drums, bass, chords, melody, pads with musical progressions
 */
void composeSongToMidi(const SongSpec& spec, const std::string& midiPath);

/**
 * Phase 8: Genre-aware composition with structured sections
 * Uses SongPlan to create EDM-style tracks with build/drop/break structure
 */
void composeGenreSongToMidi(const SongPlan& plan, const std::string& midiPath);
