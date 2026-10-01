// A minimal Standard MIDI File writer (format 1). The format is simple enough that writing it
// by hand was easier than adding a library. Composer.cpp is the only caller; tests/test_core.cpp
// parses the output back to check it. The byte layout is in MidiWriter.cpp.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

class MidiWriter {
 public:
  // ticksPerBeat is the file's time resolution; Composer.cpp passes music::TICKS_PER_BEAT.
  explicit MidiWriter(int ticksPerBeat);

  // Building a track
  // One tempo for the whole song, in bpm. It is written into track 0 as microseconds per beat.
  void setTempo(int bpm);
  // Adds an empty track and returns its index, which the add* methods below take.
  int addTrack();
  // Picks the GM instrument (0 to 127) for a channel from this tick onwards.
  void addProgramChange(int track, int tick, int channel, int program);

  // Notes
  // A note on at startTick and a note off lengthTicks later. Note and velocity are clamped to
  // the MIDI range.
  void addNote(int track, int startTick, int lengthTicks, int channel, int note, int velocity);

  // Meta events (tempo, markers)
  // A text marker at a tick; Composer.cpp writes section names this way.
  void addMarker(int track, int tick, const std::string& text);

  // Output
  // The whole .mid file as bytes: the header chunk, then one track chunk per track.
  std::string toBytes() const;

 private:
  // One MIDI event at an absolute tick. data is the status byte and its data bytes, ready to
  // write once the delta time is in front of it.
  struct Event {
    int tick;
    std::vector<uint8_t> data;
  };

  int ticksPerBeat_;
  int tempoBpm_ = 120;                     // the MIDI default if setTempo is never called
  std::vector<std::vector<Event>> tracks_;  // events per track, in the order they were added

  // Sorts one track's events by tick and turns them into the bytes of its track chunk.
  std::vector<uint8_t> encodeTrack(size_t index) const;
};
