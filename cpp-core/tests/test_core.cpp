// cpp-core's tests. A small CHECK macro instead of a test framework, so they build anywhere with
// no extra dependencies. Built with -DSOUNDCANVAS_TESTS=ON and run by ctest.
#include <cmath>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "Composer.hpp"
#include "GenreTemplate.hpp"
#include "ImageFeatures.hpp"
#include "MidiWriter.hpp"
#include "MusicTheory.hpp"
#include "SectionPlanner.hpp"
#include "json.hpp"

using json = nlohmann::json;

namespace {

int failures = 0;

#define CHECK(condition)                                                          \
  do {                                                                            \
    if (!(condition)) {                                                           \
      std::cerr << "  FAILED " << __FILE__ << ":" << __LINE__ << ": " #condition "\n"; \
      ++failures;                                                                 \
    }                                                                             \
  } while (0)

const std::vector<std::string> GENRE_NAMES = {"EDM_CHILL", "EDM_DROP", "CINEMATIC", "HOUSE"};

std::string readFile(const std::string& path) {
  std::ifstream file(path, std::ios::binary);
  if (!file) throw std::runtime_error("cannot open " + path);
  std::ostringstream bytes;
  bytes << file.rdbuf();
  return bytes.str();
}

ImageFeatures someFeatures(float brightness) {
  return {0.6f, 0.4f, 0.3f, brightness, 0.1f, 0.5f, 0.4f, 0.2f};
}

// A minimal MIDI reader, only for checking the writer's output.
struct MidiEvent {
  int tick;
  uint8_t status;  // 0xFF for meta events
  std::vector<uint8_t> data;
};

struct MidiFile {
  int format, ticksPerBeat;
  std::vector<std::vector<MidiEvent>> tracks;
};

uint32_t readBigEndian(const std::string& bytes, size_t& pos, int size) {
  uint32_t value = 0;
  for (int i = 0; i < size; ++i) value = (value << 8) | static_cast<uint8_t>(bytes.at(pos++));
  return value;
}

uint32_t readVarLen(const std::string& bytes, size_t& pos) {
  uint32_t value = 0;
  uint8_t byte;
  do {
    byte = static_cast<uint8_t>(bytes.at(pos++));
    value = (value << 7) | (byte & 0x7F);
  } while (byte & 0x80);
  return value;
}

// Throws if the bytes aren't a valid MIDI file.
MidiFile parseMidi(const std::string& bytes) {
  size_t pos = 0;
  if (bytes.substr(0, 4) != "MThd") throw std::runtime_error("missing MThd");
  pos = 4;
  if (readBigEndian(bytes, pos, 4) != 6) throw std::runtime_error("bad header length");
  MidiFile file;
  file.format = static_cast<int>(readBigEndian(bytes, pos, 2));
  int trackCount = static_cast<int>(readBigEndian(bytes, pos, 2));
  file.ticksPerBeat = static_cast<int>(readBigEndian(bytes, pos, 2));

  for (int t = 0; t < trackCount; ++t) {
    if (bytes.substr(pos, 4) != "MTrk") throw std::runtime_error("missing MTrk");
    pos += 4;
    size_t end = pos + readBigEndian(bytes, pos, 4);
    std::vector<MidiEvent> events;
    int tick = 0;
    bool ended = false;
    while (pos < end) {
      tick += static_cast<int>(readVarLen(bytes, pos));
      uint8_t status = static_cast<uint8_t>(bytes.at(pos++));
      MidiEvent event{tick, status, {}};
      if (status == 0xFF) {
        event.data.push_back(static_cast<uint8_t>(bytes.at(pos++)));  // meta type
        uint32_t length = readVarLen(bytes, pos);
        for (uint32_t i = 0; i < length; ++i) event.data.push_back(static_cast<uint8_t>(bytes.at(pos++)));
        ended = event.data[0] == 0x2F;
      } else {
        int dataBytes = (status & 0xF0) == 0xC0 ? 1 : 2;  // program change has one data byte
        for (int i = 0; i < dataBytes; ++i) event.data.push_back(static_cast<uint8_t>(bytes.at(pos++)));
      }
      events.push_back(event);
    }
    if (pos != end || !ended) throw std::runtime_error("track length or end-of-track wrong");
    file.tracks.push_back(events);
  }
  if (pos != bytes.size()) throw std::runtime_error("trailing bytes");
  return file;
}

// golden.json comes from tests/feature_parity/make_golden.py.
void featuresMatchPython() {
  const std::string root = REPO_ROOT;
  json golden = json::parse(readFile(root + "/tests/feature_parity/golden.json"));
  double tolerance = golden["tolerance"];
  double worst = 0;
  for (auto& [path, expected] : golden["images"].items()) {
    std::array<float, 8> actual = extractFeatures(readFile(root + "/" + path)).toArray();
    for (size_t i = 0; i < actual.size(); ++i) {
      double diff = std::abs(actual[i] - expected[i].get<double>());
      worst = std::max(worst, diff);
      if (diff > tolerance) {
        std::cerr << "  " << path << " " << golden["feature_names"][i].get<std::string>()
                  << ": C++ " << actual[i] << " vs Python " << expected[i] << "\n";
        ++failures;
      }
    }
  }
  std::cout << "  largest C++/Python difference: " << worst << " (allowed " << tolerance << ")\n";
}

void rejectsBytesThatAreNotAnImage() {
  bool threw = false;
  try {
    extractFeatures("definitely not a jpeg");
  } catch (const std::invalid_argument&) {
    threw = true;
  }
  CHECK(threw);
}

// A 41-byte PNG that claims to be 10000x10000 has to be rejected before decoding.
void rejectsImagesThatAreTooLarge() {
  std::string png = std::string("\x89PNG\r\n\x1a\n", 8) + std::string("\0\0\0\x0d", 4) + "IHDR" +
                    std::string("\0\0\x27\x10\0\0\x27\x10", 8) +  // width and height: 10,000
                    std::string("\x08\x02\0\0\0", 5) +            // 8-bit RGB
                    std::string(4, '\0') +                         // CRC, which stb doesn't check
                    std::string("\0\0\0\0", 4) + "IDAT";
  bool threw = false;
  try {
    extractFeatures(png);
  } catch (const std::invalid_argument& error) {
    threw = std::string(error.what()).find("megapixels") != std::string::npos;
  }
  CHECK(threw);
}

void rejectsFeaturesOutOfRange() {
  std::array<float, 8> valid = someFeatures(0.5f).toArray();
  CHECK(ImageFeatures::fromArray(valid).brightness == 0.5f);

  for (auto [index, value] : std::vector<std::pair<size_t, float>>{
           {3, -0.1f}, {3, 1.5f}, {0, NAN}, {7, 0.6f}}) {
    std::array<float, 8> bad = valid;
    bad[index] = value;
    bool threw = false;
    try {
      ImageFeatures::fromArray(bad);
    } catch (const std::invalid_argument&) {
      threw = true;
    }
    CHECK(threw);
  }
}

void parsesGenreNames() {
  for (const std::string& name : GENRE_NAMES) CHECK(templateFor(parseGenre(name)).name == name);
  bool threw = false;
  try {
    parseGenre("JAZZ");
  } catch (const std::invalid_argument&) {
    threw = true;
  }
  CHECK(threw);
}

// A 15-character pattern would drift off the beat without any error.
void genreTemplatesAreWellFormed() {
  for (const std::string& name : GENRE_NAMES) {
    const GenreTemplate& genre = templateFor(parseGenre(name));
    const Patterns& p = genre.patterns;
    for (const std::string* pattern : {&p.kick, &p.snare, &p.hat, &p.openHat, &p.bass, &p.chords}) {
      CHECK(pattern->empty() || static_cast<int>(pattern->size()) == music::STEPS_PER_BAR);
    }
    CHECK(genre.melody.size() == 8);
    CHECK(genre.minTempo <= genre.maxTempo);
    CHECK(!genre.progression.empty());
    CHECK(!genre.sections.empty());
    for (const Section& section : genre.sections) CHECK(section.energy >= 0 && section.energy <= 1);
  }
}

void tempoFollowsBrightness() {
  for (const std::string& name : GENRE_NAMES) {
    Genre genre = parseGenre(name);
    CHECK(planSong(someFeatures(0.0f), genre).tempoBpm == templateFor(genre).minTempo);
    CHECK(planSong(someFeatures(1.0f), genre).tempoBpm == templateFor(genre).maxTempo);
    for (const Section& section : planSong(someFeatures(0.5f), genre).sections) {
      CHECK(section.energy <= 1.0f);
    }
  }
}

void midiWriterWritesTheStandardFormat() {
  MidiWriter midi(480);
  midi.setTempo(120);
  int track = midi.addTrack();
  midi.addNote(track, 200, 100, 0, 60, 100);  // a delta of 200 needs two bytes
  MidiFile file = parseMidi(midi.toBytes());

  CHECK(file.format == 1);
  CHECK(file.ticksPerBeat == 480);
  CHECK(file.tracks.size() == 1);
  const std::vector<MidiEvent>& events = file.tracks[0];
  CHECK(events.size() == 4);  // tempo, note on, note off, end of track
  CHECK(events[0].status == 0xFF && events[0].data[0] == 0x51);
  uint32_t microsecondsPerBeat = (events[0].data[1] << 16) | (events[0].data[2] << 8) | events[0].data[3];
  CHECK(microsecondsPerBeat == 500000);  // 120 bpm
  CHECK(events[1].tick == 200 && events[1].status == 0x90 && events[1].data[0] == 60);
  CHECK(events[2].tick == 300 && events[2].status == 0x80);
}

// Every genre makes a file that parses, has no stuck notes, and has one marker per section.
void composesValidMidiForEveryGenre() {
  for (const std::string& name : GENRE_NAMES) {
    SongPlan plan = planSong(someFeatures(0.5f), parseGenre(name));
    MidiFile file = parseMidi(composeMidi(plan));
    CHECK(file.tracks.size() == 5);  // drums, bass, chords, lead, pad

    int totalBars = 0;
    for (const Section& section : plan.sections) totalBars += section.bars;
    int songEnd = totalBars * music::TICKS_PER_BAR;

    int notes = 0;
    std::vector<std::string> markers;
    for (const std::vector<MidiEvent>& track : file.tracks) {
      std::map<int, int> held;  // notes still on, keyed by channel * 128 + note
      for (const MidiEvent& event : track) {
        int kind = event.status & 0xF0;
        int key = (event.status & 0x0F) * 128 + event.data.at(0);
        if (kind == 0x90) {
          ++held[key];
          ++notes;
        } else if (kind == 0x80) {
          --held[key];
          CHECK(event.tick <= songEnd);
        } else if (event.status == 0xFF && event.data[0] == 0x06) {
          markers.emplace_back(event.data.begin() + 1, event.data.end());
        }
      }
      for (auto& [key, count] : held) CHECK(count == 0);
    }
    CHECK(notes > 0);
    CHECK(markers.size() == plan.sections.size());
    for (size_t i = 0; i < markers.size() && i < plan.sections.size(); ++i) {
      CHECK(markers[i] == sectionName(plan.sections[i].type));
    }
  }
}

}  // namespace

int main() {
  const std::vector<std::pair<std::string, std::function<void()>>> tests = {
      {"features match Python", featuresMatchPython},
      {"rejects bytes that are not an image", rejectsBytesThatAreNotAnImage},
      {"rejects images that are too large", rejectsImagesThatAreTooLarge},
      {"rejects features out of range", rejectsFeaturesOutOfRange},
      {"parses genre names", parsesGenreNames},
      {"genre templates are well formed", genreTemplatesAreWellFormed},
      {"tempo follows brightness", tempoFollowsBrightness},
      {"MIDI writer writes the standard format", midiWriterWritesTheStandardFormat},
      {"composes valid MIDI for every genre", composesValidMidiForEveryGenre},
  };
  for (const auto& [name, test] : tests) {
    std::cout << name << "\n";
    try {
      test();
    } catch (const std::exception& error) {
      std::cerr << "  FAILED with exception: " << error.what() << "\n";
      ++failures;
    }
  }
  std::cout << (failures == 0 ? "all tests passed\n" : "some tests FAILED\n");
  return failures == 0 ? 0 : 1;
}
