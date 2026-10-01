// Writes a Standard MIDI File by hand: an MThd header chunk, then one MTrk chunk per track. Events
// are stored with absolute ticks and only turned into delta times when the file is written.
// Called from Composer.cpp. tests/test_core.cpp reads the bytes back with its own small parser,
// and audio-producer/midi.py reads the same file with mido to render it.
#include "MidiWriter.hpp"

#include <algorithm>

namespace {

// Status bytes: the top 4 bits are the event type and the bottom 4 the channel.
// So NOTE_ON | 9 is 0x99, a note on for channel 9 (the drums).
constexpr uint8_t NOTE_OFF = 0x80;
constexpr uint8_t NOTE_ON = 0x90;
constexpr uint8_t PROGRAM_CHANGE = 0xC0;

// Meta events start with 0xFF, then a type byte, a length and the data. They carry file
// information instead of sound.
constexpr uint8_t META = 0xFF;
constexpr uint8_t META_MARKER = 0x06;        // text marker, used for section names
constexpr uint8_t META_TEMPO = 0x51;         // tempo as 3 bytes of microseconds per beat
constexpr uint8_t META_END_OF_TRACK = 0x2F;  // required as the last event of every track

constexpr int MICROSECONDS_PER_MINUTE = 60000000;

// 7 bits per byte, with the top bit set on every byte except the last.
// The lowest 7 bits are taken first (value & 0x7F) and become the last byte. Each value >>= 7
// moves on to the next 7 bits, which get 0x80 added to mean "more bytes follow". The bytes were
// collected lowest first, so they are written in reverse. For example 200 becomes 0x81 0x48.
void writeVarLen(std::vector<uint8_t>& out, uint32_t value) {
  std::vector<uint8_t> bytes = {static_cast<uint8_t>(value & 0x7F)};
  while (value >>= 7) {
    bytes.push_back(static_cast<uint8_t>((value & 0x7F) | 0x80));
  }
  out.insert(out.end(), bytes.rbegin(), bytes.rend());
}

// MIDI writes multi-byte numbers most-significant byte first.
// Each pass shifts the wanted byte down to the bottom and masks it with 0xFF.
void writeBigEndian(std::vector<uint8_t>& out, uint32_t value, int size) {
  for (int shift = (size - 1) * 8; shift >= 0; shift -= 8) {
    out.push_back(static_cast<uint8_t>((value >> shift) & 0xFF));
  }
}

}  // namespace

MidiWriter::MidiWriter(int ticksPerBeat) : ticksPerBeat_(ticksPerBeat) {}

// Only stored here; encodeTrack writes it into track 0.
void MidiWriter::setTempo(int bpm) { tempoBpm_ = bpm; }

int MidiWriter::addTrack() {
  tracks_.emplace_back();
  return static_cast<int>(tracks_.size()) - 1;
}

// Two bytes: 0xC0 plus the channel, then the program number.
void MidiWriter::addProgramChange(int track, int tick, int channel, int program) {
  tracks_[track].push_back({tick, {static_cast<uint8_t>(PROGRAM_CHANGE | channel),
                                   static_cast<uint8_t>(program)}});
}

// A note is two events: note on at the start and note off at the end.
void MidiWriter::addNote(int track, int startTick, int lengthTicks, int channel, int note,
                         int velocity) {
  // MIDI data bytes are 7 bits, so 0 to 127. Velocity starts at 1 because a note on with
  // velocity 0 is read as a note off.
  auto pitch = static_cast<uint8_t>(std::clamp(note, 0, 127));
  auto loudness = static_cast<uint8_t>(std::clamp(velocity, 1, 127));
  tracks_[track].push_back({startTick, {static_cast<uint8_t>(NOTE_ON | channel), pitch, loudness}});
  tracks_[track].push_back(
      {startTick + lengthTicks, {static_cast<uint8_t>(NOTE_OFF | channel), pitch, 0}});
}

// A text marker at this tick, written as a MIDI meta event. Used for section names.
// Bytes: 0xFF 0x06, the text length as a var-length number, then the text itself.
void MidiWriter::addMarker(int track, int tick, const std::string& text) {
  std::vector<uint8_t> data = {META, META_MARKER};
  writeVarLen(data, static_cast<uint32_t>(text.size()));
  data.insert(data.end(), text.begin(), text.end());
  tracks_[track].push_back({tick, data});
}

// Track chunk body: the tempo (track 0 only), every event with its delta time, then the end of
// track event. toBytes adds the "MTrk" tag and length in front.
std::vector<uint8_t> MidiWriter::encodeTrack(size_t index) const {
  // Events were added part by part, so sort them by time. stable_sort keeps same-tick events in
  // the order they were added, so a program change stays ahead of the first note.
  std::vector<Event> events = tracks_[index];
  std::stable_sort(events.begin(), events.end(),
                   [](const Event& a, const Event& b) { return a.tick < b.tick; });

  std::vector<uint8_t> out;
  if (index == 0) {
    // Tempo goes in track 0, in microseconds per beat.
    // Bytes: delta 0, 0xFF 0x51, length 3, then 60,000,000 / bpm in 3 bytes (120 bpm is 500000).
    out.insert(out.end(), {0, META, META_TEMPO, 3});
    writeBigEndian(out, MICROSECONDS_PER_MINUTE / tempoBpm_, 3);
  }

  // Each event is written as the ticks since the previous one, then its bytes.
  int previousTick = 0;
  for (const Event& event : events) {
    writeVarLen(out, static_cast<uint32_t>(event.tick - previousTick));
    out.insert(out.end(), event.data.begin(), event.data.end());
    previousTick = event.tick;
  }
  // Delta 0, 0xFF 0x2F, length 0. The format requires it as the last event of a track.
  out.insert(out.end(), {0, META, META_END_OF_TRACK, 0});
  return out;
}

// The whole file: one header chunk, then one track chunk per track.
std::string MidiWriter::toBytes() const {
  // Header chunk: "MThd", length 6, then format, track count and ticks per beat, 2 bytes each.
  std::vector<uint8_t> out = {'M', 'T', 'h', 'd'};
  writeBigEndian(out, 6, 4);  // header length
  writeBigEndian(out, 1, 2);  // format 1: the tracks play at the same time
  writeBigEndian(out, static_cast<uint32_t>(tracks_.size()), 2);
  writeBigEndian(out, ticksPerBeat_, 2);

  // Track chunks: "MTrk", the body length in 4 bytes, then the body from encodeTrack.
  for (size_t i = 0; i < tracks_.size(); ++i) {
    std::vector<uint8_t> track = encodeTrack(i);
    out.insert(out.end(), {'M', 'T', 'r', 'k'});
    writeBigEndian(out, static_cast<uint32_t>(track.size()), 4);
    out.insert(out.end(), track.begin(), track.end());
  }
  // std::string is used as a plain byte buffer, since that is what httplib sends.
  return std::string(out.begin(), out.end());
}
