#pragma once

#include "SongSpec.hpp"
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
