#include "MidiWriter.hpp"

#include <algorithm>
#include <fstream>
#include <stdexcept>

MidiWriter::MidiWriter(int ticksPerQuarter)
    : ticksPerQuarter_(ticksPerQuarter),
      tempoBpm_(120.0f),
      timeSignatureNumerator_(4),
      timeSignatureDenominator_(4) {}

void MidiWriter::setTempo(float bpm) { tempoBpm_ = bpm; }

void MidiWriter::setTimeSignature(int numerator, int denominator) {
  timeSignatureNumerator_ = numerator;
  timeSignatureDenominator_ = denominator;
}

int MidiWriter::addTrack(const std::string& name) {
  tracks_.push_back({name, {}});
  return static_cast<int>(tracks_.size()) - 1;
}

void MidiWriter::addNoteOn(int track, int tick, int channel, int note,
                           int velocity) {
  if (track < 0 || track >= static_cast<int>(tracks_.size())) return;

  MidiEvent event;
  event.tick = tick;
  event.data = {static_cast<uint8_t>(0x90 | (channel & 0x0F)),
                static_cast<uint8_t>(note & 0x7F),
                static_cast<uint8_t>(velocity & 0x7F)};
  tracks_[track].events.push_back(event);
}

void MidiWriter::addNoteOff(int track, int tick, int channel, int note) {
  if (track < 0 || track >= static_cast<int>(tracks_.size())) return;

  MidiEvent event;
  event.tick = tick;
  event.data = {
      static_cast<uint8_t>(0x80 | (channel & 0x0F)),
      static_cast<uint8_t>(note & 0x7F),
      static_cast<uint8_t>(0x40)  // Default release velocity
  };
  tracks_[track].events.push_back(event);
}

void MidiWriter::addProgramChange(int track, int tick, int channel,
                                  int program) {
  if (track < 0 || track >= static_cast<int>(tracks_.size())) return;

  MidiEvent event;
  event.tick = tick;
  event.data = {static_cast<uint8_t>(0xC0 | (channel & 0x0F)),
                static_cast<uint8_t>(program & 0x7F)};
  tracks_[track].events.push_back(event);
}

void MidiWriter::writeVarLen(std::vector<uint8_t>& out, uint32_t value) {
  // MIDI variable-length encoding
  uint32_t buffer = value & 0x7F;
  while ((value >>= 7) > 0) {
    buffer <<= 8;
    buffer |= 0x80;
    buffer += (value & 0x7F);
  }

  while (true) {
    out.push_back(static_cast<uint8_t>(buffer & 0xFF));
    if (buffer & 0x80) {
      buffer >>= 8;
    } else {
      break;
    }
  }
}

void MidiWriter::writeU16(std::vector<uint8_t>& out, uint16_t value) {
  out.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
  out.push_back(static_cast<uint8_t>(value & 0xFF));
}

void MidiWriter::writeU32(std::vector<uint8_t>& out, uint32_t value) {
  out.push_back(static_cast<uint8_t>((value >> 24) & 0xFF));
  out.push_back(static_cast<uint8_t>((value >> 16) & 0xFF));
  out.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
  out.push_back(static_cast<uint8_t>(value & 0xFF));
}

std::vector<uint8_t> MidiWriter::buildTrackData(int trackIndex) {
  std::vector<uint8_t> trackData;

  // Sort events by tick
  auto& track = tracks_[trackIndex];
  std::sort(track.events.begin(), track.events.end());

  // First track gets tempo and time signature meta events
  if (trackIndex == 0) {
    // Track name (optional)
    if (!track.name.empty()) {
      writeVarLen(trackData, 0);  // Delta time 0
      trackData.push_back(0xFF);  // Meta event
      trackData.push_back(0x03);  // Track name
      writeVarLen(trackData, static_cast<uint32_t>(track.name.size()));
      for (char c : track.name) {
        trackData.push_back(static_cast<uint8_t>(c));
      }
    }

    // Set tempo
    writeVarLen(trackData, 0);  // Delta time 0
    trackData.push_back(0xFF);  // Meta event
    trackData.push_back(0x51);  // Set tempo
    trackData.push_back(0x03);  // Length = 3 bytes

    // Microseconds per quarter note
    uint32_t microsecondsPerQuarter =
        static_cast<uint32_t>(60000000.0f / tempoBpm_);
    trackData.push_back(
        static_cast<uint8_t>((microsecondsPerQuarter >> 16) & 0xFF));
    trackData.push_back(
        static_cast<uint8_t>((microsecondsPerQuarter >> 8) & 0xFF));
    trackData.push_back(static_cast<uint8_t>(microsecondsPerQuarter & 0xFF));

    // Time signature
    writeVarLen(trackData, 0);  // Delta time 0
    trackData.push_back(0xFF);  // Meta event
    trackData.push_back(0x58);  // Time signature
    trackData.push_back(0x04);  // Length = 4 bytes
    trackData.push_back(static_cast<uint8_t>(timeSignatureNumerator_));
    // Denominator as power of 2 (4 = 2^2)
    int denomLog2 = 0;
    int denom = timeSignatureDenominator_;
    while (denom > 1) {
      denom >>= 1;
      denomLog2++;
    }
    trackData.push_back(static_cast<uint8_t>(denomLog2));
    trackData.push_back(0x18);  // MIDI clocks per metronome click
    trackData.push_back(0x08);  // 32nd notes per quarter note
  }

  // Add all events with delta times
  int lastTick = 0;
  for (const auto& event : track.events) {
    int deltaTicks = event.tick - lastTick;
    if (deltaTicks < 0) deltaTicks = 0;

    writeVarLen(trackData, static_cast<uint32_t>(deltaTicks));
    for (uint8_t byte : event.data) {
      trackData.push_back(byte);
    }

    lastTick = event.tick;
  }

  // End of track meta event
  writeVarLen(trackData, 0);
  trackData.push_back(0xFF);
  trackData.push_back(0x2F);
  trackData.push_back(0x00);

  return trackData;
}

void MidiWriter::write(const std::string& filepath) {
  std::ofstream file(filepath, std::ios::binary);
  if (!file) {
    throw std::runtime_error("Failed to create MIDI file: " + filepath);
  }

  std::vector<uint8_t> data;

  // --- MIDI Header Chunk ---
  // "MThd"
  data.push_back('M');
  data.push_back('T');
  data.push_back('h');
  data.push_back('d');

  // Chunk length (always 6 for header)
  writeU32(data, 6);

  // Format 1 (multi-track)
  writeU16(data, 1);

  // Number of tracks
  writeU16(data, static_cast<uint16_t>(tracks_.size()));

  // Ticks per quarter note
  writeU16(data, static_cast<uint16_t>(ticksPerQuarter_));

  // --- Track Chunks ---
  for (size_t i = 0; i < tracks_.size(); ++i) {
    std::vector<uint8_t> trackData = buildTrackData(static_cast<int>(i));

    // "MTrk"
    data.push_back('M');
    data.push_back('T');
    data.push_back('r');
    data.push_back('k');

    // Track length
    writeU32(data, static_cast<uint32_t>(trackData.size()));

    // Track data
    data.insert(data.end(), trackData.begin(), trackData.end());
  }

  // Write to file
  file.write(reinterpret_cast<const char*>(data.data()), data.size());
  file.close();
}

void MidiWriter::writeSingleTrack(int trackIndex, const std::string& filepath) {
  if (trackIndex < 0 || trackIndex >= static_cast<int>(tracks_.size())) {
    throw std::runtime_error("Invalid track index");
  }

  std::ofstream file(filepath, std::ios::binary);
  if (!file) {
    throw std::runtime_error("Cannot open file for writing: " + filepath);
  }

  std::vector<uint8_t> data;

  // --- Header Chunk ---
  data.push_back('M');
  data.push_back('T');
  data.push_back('h');
  data.push_back('d');

  // Chunk length (always 6 for header)
  writeU32(data, 6);

  // Format 0 (single track with tempo)
  writeU16(data, 0);

  // Number of tracks (1)
  writeU16(data, 1);

  // Ticks per quarter note
  writeU16(data, static_cast<uint16_t>(ticksPerQuarter_));

  // --- Single Track Chunk ---
  std::vector<uint8_t> trackData = buildTrackData(trackIndex);

  // "MTrk"
  data.push_back('M');
  data.push_back('T');
  data.push_back('r');
  data.push_back('k');

  // Track length
  writeU32(data, static_cast<uint32_t>(trackData.size()));

  // Track data
  data.insert(data.end(), trackData.begin(), trackData.end());

  // Write to file
  file.write(reinterpret_cast<const char*>(data.data()), data.size());
  file.close();
}

std::map<std::string, std::string> MidiWriter::writeSeparateStems(
    const std::string& baseDir) {
  std::map<std::string, std::string> result;

  for (size_t i = 0; i < tracks_.size(); ++i) {
    std::string trackName = tracks_[i].name;
    if (trackName.empty()) {
      trackName = "track" + std::to_string(i);
    }

    std::string filepath = baseDir + "/" + trackName + ".mid";
    writeSingleTrack(static_cast<int>(i), filepath);
    result[trackName] = filepath;
  }

  return result;
}
