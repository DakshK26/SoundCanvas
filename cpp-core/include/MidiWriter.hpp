// A minimal Standard MIDI File (format 1) writer.
// Collects note events per track and serializes them to bytes.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

class MidiWriter {
 public:
  explicit MidiWriter(int ticksPerBeat);

  void setTempo(int bpm);
  int addTrack();
  void addProgramChange(int track, int tick, int channel, int program);
  void addNote(int track, int startTick, int lengthTicks, int channel, int note, int velocity);

  // A text marker such as "drop". The audio producer uses these to place effects.
  void addMarker(int track, int tick, const std::string& text);

  // The complete .mid file.
  std::string toBytes() const;

 private:
  struct Event {
    int tick;
    std::vector<uint8_t> data;
  };

  int ticksPerBeat_;
  int tempoBpm_ = 120;
  std::vector<std::vector<Event>> tracks_;

  std::vector<uint8_t> encodeTrack(size_t index) const;
};
