#pragma once

#include <map>
#include <string>

#include "SectionPlanner.hpp"
#include "SongSpec.hpp"

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

/**
 * Compose and export separate MIDI stems for multi-track production
 * @param spec Song specification
 * @param outputDir Directory to write individual stem MIDI files
 * @return Map of stem name -> filepath
 */
std::map<std::string, std::string> composeSongToStems(
    const SongSpec& spec, const std::string& outputDir);
