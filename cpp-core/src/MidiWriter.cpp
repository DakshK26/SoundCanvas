// events -> Standard MIDI File bytes. followed the MIDI 1.0 SMF spec
// file = MThd header chunk, then one MTrk chunk per track
#include "MidiWriter.hpp"

#include <algorithm>

namespace {

// status byte: high nibble = event type, low nibble = channel (so NOTE_ON | 9 = drum hit)
constexpr uint8_t NOTE_OFF = 0x80;
constexpr uint8_t NOTE_ON = 0x90;
constexpr uint8_t PROGRAM_CHANGE = 0xC0;

// meta events = 0xFF, type, length, data
constexpr uint8_t META = 0xFF;
constexpr uint8_t META_MARKER = 0x06;
constexpr uint8_t META_TEMPO = 0x51;
constexpr uint8_t META_END_OF_TRACK = 0x2F;

constexpr int MICROSECONDS_PER_MINUTE = 60000000;

// "variable length quantity" - 7 bits per byte, top bit = "more bytes coming".
// build it backwards (low bits first) then reverse in
void writeVarLen(std::vector<uint8_t>& out, uint32_t value) {
  std::vector<uint8_t> bytes = {static_cast<uint8_t>(value & 0x7F)};
  while (value >>= 7) {
    bytes.push_back(static_cast<uint8_t>((value & 0x7F) | 0x80));
  }
  out.insert(out.end(), bytes.rbegin(), bytes.rend());
}

// midi is big endian everywhere
void writeBigEndian(std::vector<uint8_t>& out, uint32_t value, int size) {
  for (int shift = (size - 1) * 8; shift >= 0; shift -= 8) {
    out.push_back(static_cast<uint8_t>((value >> shift) & 0xFF));
  }
}

}  // namespace

MidiWriter::MidiWriter(int ticksPerBeat) : ticksPerBeat_(ticksPerBeat) {}

void MidiWriter::setTempo(int bpm) { tempoBpm_ = bpm; }

int MidiWriter::addTrack() {
  tracks_.emplace_back();
  return static_cast<int>(tracks_.size()) - 1;
}

void MidiWriter::addProgramChange(int track, int tick, int channel, int program) {
  tracks_[track].push_back({tick, {static_cast<uint8_t>(PROGRAM_CHANGE | channel),
                                   static_cast<uint8_t>(program)}});
}

void MidiWriter::addNote(int track, int startTick, int lengthTicks, int channel, int note,
                         int velocity) {
  auto pitch = static_cast<uint8_t>(std::clamp(note, 0, 127));
  auto loudness = static_cast<uint8_t>(std::clamp(velocity, 1, 127));
  tracks_[track].push_back({startTick, {static_cast<uint8_t>(NOTE_ON | channel), pitch, loudness}});
  tracks_[track].push_back(
      {startTick + lengthTicks, {static_cast<uint8_t>(NOTE_OFF | channel), pitch, 0}});
}

void MidiWriter::addMarker(int track, int tick, const std::string& text) {
  std::vector<uint8_t> data = {META, META_MARKER};
  writeVarLen(data, static_cast<uint32_t>(text.size()));
  data.insert(data.end(), text.begin(), text.end());
  tracks_[track].push_back({tick, data});
}

std::vector<uint8_t> MidiWriter::encodeTrack(size_t index) const {
  std::vector<Event> events = tracks_[index];
  std::stable_sort(events.begin(), events.end(),
                   [](const Event& a, const Event& b) { return a.tick < b.tick; });

  std::vector<uint8_t> out;
  if (index == 0) {
    // tempo lives in track 0, as microseconds per beat (not bpm!)
    out.insert(out.end(), {0, META, META_TEMPO, 3});
    writeBigEndian(out, MICROSECONDS_PER_MINUTE / tempoBpm_, 3);
  }

  int previousTick = 0;
  for (const Event& event : events) {
    writeVarLen(out, static_cast<uint32_t>(event.tick - previousTick));
    out.insert(out.end(), event.data.begin(), event.data.end());
    previousTick = event.tick;
  }
  out.insert(out.end(), {0, META, META_END_OF_TRACK, 0});
  return out;
}

std::string MidiWriter::toBytes() const {
  std::vector<uint8_t> out = {'M', 'T', 'h', 'd'};
  writeBigEndian(out, 6, 4);                // header length, always 6
  writeBigEndian(out, 1, 2);                // format 1 = multiple tracks played at the same time
  writeBigEndian(out, static_cast<uint32_t>(tracks_.size()), 2);
  writeBigEndian(out, ticksPerBeat_, 2);

  for (size_t i = 0; i < tracks_.size(); ++i) {
    std::vector<uint8_t> track = encodeTrack(i);
    out.insert(out.end(), {'M', 'T', 'r', 'k'});
    writeBigEndian(out, static_cast<uint32_t>(track.size()), 4);
    out.insert(out.end(), track.begin(), track.end());
  }
  return std::string(out.begin(), out.end());
}
