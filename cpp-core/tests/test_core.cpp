// cpp-core's tests. A small CHECK macro instead of a test framework, so they build anywhere with
// no extra dependencies. Built with -DSOUNDCANVAS_TESTS=ON and run by ctest.
// Covers ImageFeatures.cpp, GenreTemplate.cpp, SongPlanner.cpp, Composer.cpp and MidiWriter.cpp.
// HttpServer.cpp is not linked in, so no server is started.
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
#include "SongPlanner.hpp"
#include "json.hpp"

using json = nlohmann::json;

namespace {

// Counted instead of aborting, so one run reports every failure.
int failures = 0;

// Prints the file, line and the condition's own text (#condition) when it is false. The
// do { } while (0) makes the macro act like one statement after an if.
#define CHECK(condition)                                                          \
  do {                                                                            \
    if (!(condition)) {                                                           \
      std::cerr << "  FAILED " << __FILE__ << ":" << __LINE__ << ": " #condition "\n"; \
      ++failures;                                                                 \
    }                                                                             \
  } while (0)

// The same four names as ml/genres.py and parseGenre in GenreTemplate.cpp.
const std::vector<std::string> GENRE_NAMES = {"EDM_CHILL", "EDM_DROP", "CINEMATIC", "HOUSE"};

// Whole file as bytes. Binary mode, so on Windows the image bytes come back unchanged.
std::string readFile(const std::string& path) {
  std::ifstream file(path, std::ios::binary);
  if (!file) throw std::runtime_error("cannot open " + path);
  std::ostringstream bytes;
  bytes << file.rdbuf();
  return bytes.str();
}

// Fixed, in-range features where only brightness varies, since brightness sets the tempo.
ImageFeatures someFeatures(float brightness) {
  return {0.6f, 0.4f, 0.3f, brightness, 0.1f, 0.5f, 0.4f, 0.2f};
}

// A minimal MIDI reader, only for checking the writer's output.
// It is written separately from MidiWriter.cpp, so a mistake in the writer can't hide itself.
struct MidiEvent {
  int tick;                   // absolute, rebuilt by adding up the deltas
  uint8_t status;             // 0xFF for meta events
  std::vector<uint8_t> data;  // for meta events, the type byte then the payload
};

// The header fields and each track's events.
struct MidiFile {
  int format, ticksPerBeat;
  std::vector<std::vector<MidiEvent>> tracks;
};

// The reverse of writeBigEndian in MidiWriter.cpp: shift left a byte, add the next one.
uint32_t readBigEndian(const std::string& bytes, size_t& pos, int size) {
  uint32_t value = 0;
  for (int i = 0; i < size; ++i) value = (value << 8) | static_cast<uint8_t>(bytes.at(pos++));
  return value;
}

// The reverse of writeVarLen in MidiWriter.cpp: 7 bits from each byte, and keep reading while
// the top bit (0x80) is set.
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
  // Header chunk: "MThd", length 6, format, track count, ticks per beat.
  size_t pos = 0;
  if (bytes.substr(0, 4) != "MThd") throw std::runtime_error("missing MThd");
  pos = 4;
  if (readBigEndian(bytes, pos, 4) != 6) throw std::runtime_error("bad header length");
  MidiFile file;
  file.format = static_cast<int>(readBigEndian(bytes, pos, 2));
  int trackCount = static_cast<int>(readBigEndian(bytes, pos, 2));
  file.ticksPerBeat = static_cast<int>(readBigEndian(bytes, pos, 2));

  // Each track chunk: "MTrk", its length, then delta-time and event pairs up to that length.
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
      // A meta event carries its own length; a channel event's length depends on its type.
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
    // The chunk length written by toBytes must be exact, and 0x2F must close every track.
    if (pos != end || !ended) throw std::runtime_error("track length or end-of-track wrong");
    file.tracks.push_back(events);
  }
  if (pos != bytes.size()) throw std::runtime_error("trailing bytes");
  return file;
}

// Rule: ImageFeatures.cpp gives the same 8 numbers as ml/features.py, which the model was
// trained on. golden.json holds Python's answers for the photos it lists.
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
      // Each feature of each photo must be within the tolerance stored in golden.json.
      if (diff > tolerance) {
        std::cerr << "  " << path << " " << golden["feature_names"][i].get<std::string>()
                  << ": C++ " << actual[i] << " vs Python " << expected[i] << "\n";
        ++failures;
      }
    }
  }
  std::cout << "  largest C++/Python difference: " << worst << " (allowed " << tolerance << ")\n";
}

// Rule: bytes stb_image can't decode throw invalid_argument in ImageFeatures.cpp, so
// HttpServer.cpp answers 400 and the worker doesn't retry.
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
// Rule: the MAX_PIXELS header check in ImageFeatures.cpp runs before stbi_load_from_memory.
// The bytes are a PNG signature, an IHDR chunk and an empty IDAT.
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
    // The message must be the size error, not a decode error, to prove the check ran first.
    threw = std::string(error.what()).find("megapixels") != std::string::npos;
  }
  CHECK(threw);
}

// Rule: ImageFeatures::fromArray in ImageFeatures.cpp rejects anything /compose shouldn't get.
void rejectsFeaturesOutOfRange() {
  // A valid array goes through unchanged.
  std::array<float, 8> valid = someFeatures(0.5f).toArray();
  CHECK(ImageFeatures::fromArray(valid).brightness == 0.5f);

  // Below 0, above 1, NaN, and contrast above its 0.5 ceiling must each throw.
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

// Rule: parseGenre and templateFor in GenreTemplate.cpp accept exactly the names in
// ml/genres.py and map each to its own template.
void parsesGenreNames() {
  for (const std::string& name : GENRE_NAMES) CHECK(templateFor(parseGenre(name)).name == name);
  // An unknown genre must throw invalid_argument so /compose answers 400.
  bool threw = false;
  try {
    parseGenre("JAZZ");
  } catch (const std::invalid_argument&) {
    threw = true;
  }
  CHECK(threw);
}

// A 15-character pattern would drift off the beat without any error.
// Rule: every recipe in GenreTemplate.cpp has the shape Composer.cpp assumes.
void genreTemplatesAreWellFormed() {
  for (const std::string& name : GENRE_NAMES) {
    const GenreTemplate& genre = templateFor(parseGenre(name));
    const Patterns& p = genre.patterns;
    // Patterns are empty (part unused) or exactly STEPS_PER_BAR from MusicTheory.hpp.
    for (const std::string* pattern : {&p.kick, &p.snare, &p.hat, &p.openHat, &p.bass, &p.chords}) {
      CHECK(pattern->empty() || static_cast<int>(pattern->size()) == music::STEPS_PER_BAR);
    }
    // playLead in Composer.cpp plays one melody entry per eighth, 8 per bar.
    CHECK(genre.melody.size() == 8);
    // pickTempo in SongPlanner.cpp needs a range that isn't upside down.
    CHECK(genre.minTempo <= genre.maxTempo);
    // composeMidi takes bar % progression.size(), which would divide by zero if empty.
    CHECK(!genre.progression.empty());
    CHECK(!genre.sections.empty());
    // Energy is documented as 0 to 1 in GenreTemplate.hpp.
    for (const Section& section : genre.sections) CHECK(section.energy >= 0 && section.energy <= 1);
  }
}

// Rule: pickTempo in SongPlanner.cpp maps brightness 0 and 1 to the genre's tempo ends, and the
// drop boost in planSong never pushes energy past 1.
void tempoFollowsBrightness() {
  for (const std::string& name : GENRE_NAMES) {
    Genre genre = parseGenre(name);
    CHECK(planSong(someFeatures(0.0f), genre).tempoBpm == templateFor(genre).minTempo);
    CHECK(planSong(someFeatures(1.0f), genre).tempoBpm == templateFor(genre).maxTempo);
    // Drops that start at 1.0 in GenreTemplate.cpp must stay at 1 after the boost.
    for (const Section& section : planSong(someFeatures(0.5f), genre).sections) {
      CHECK(section.energy <= 1.0f);
    }
  }
}

// Rule: MidiWriter.cpp writes a valid Standard MIDI File, with the header fields, the tempo in
// microseconds per beat, var-length deltas, and note on and off at the right ticks.
void midiWriterWritesTheStandardFormat() {
  MidiWriter midi(480);
  midi.setTempo(120);
  int track = midi.addTrack();
  midi.addNote(track, 200, 100, 0, 60, 100);  // a delta of 200 needs two bytes
  MidiFile file = parseMidi(midi.toBytes());

  // Header chunk fields from toBytes.
  CHECK(file.format == 1);
  CHECK(file.ticksPerBeat == 480);
  CHECK(file.tracks.size() == 1);
  const std::vector<MidiEvent>& events = file.tracks[0];
  CHECK(events.size() == 4);  // tempo, note on, note off, end of track
  // Track 0 starts with the tempo meta event (0xFF 0x51) from encodeTrack.
  CHECK(events[0].status == 0xFF && events[0].data[0] == 0x51);
  // The 3 tempo bytes put back together, most significant first.
  uint32_t microsecondsPerBeat = (events[0].data[1] << 16) | (events[0].data[2] << 8) | events[0].data[3];
  CHECK(microsecondsPerBeat == 500000);  // 120 bpm
  // Note on (0x90) at 200 proves the two-byte delta decoded right; note off (0x80) lands at
  // start plus length.
  CHECK(events[1].tick == 200 && events[1].status == 0x90 && events[1].data[0] == 60);
  CHECK(events[2].tick == 300 && events[2].status == 0x80);
}

// Every genre makes a file that parses, has no stuck notes, and has one marker per section.
// Rule: composeMidi in Composer.cpp gives audio-producer/app.py a file it can render, and the
// marker names audio-producer/fx.py looks for.
void composesValidMidiForEveryGenre() {
  for (const std::string& name : GENRE_NAMES) {
    SongPlan plan = planSong(someFeatures(0.5f), parseGenre(name));
    MidiFile file = parseMidi(composeMidi(plan));
    CHECK(file.tracks.size() == 5);  // drums, bass, chords, lead, pad

    // The last tick of the song, from the section lengths in the plan.
    int totalBars = 0;
    for (const Section& section : plan.sections) totalBars += section.bars;
    int songEnd = totalBars * music::TICKS_PER_BAR;

    int notes = 0;
    std::vector<std::string> markers;
    for (const std::vector<MidiEvent>& track : file.tracks) {
      std::map<int, int> held;  // notes still on, keyed by channel * 128 + note
      for (const MidiEvent& event : track) {
        // Top 4 bits are the event type, bottom 4 the channel, as in MidiWriter.cpp.
        int kind = event.status & 0xF0;
        int key = (event.status & 0x0F) * 128 + event.data.at(0);
        if (kind == 0x90) {
          ++held[key];
          ++notes;
        } else if (kind == 0x80) {
          --held[key];
          // No note may ring past the last bar.
          CHECK(event.tick <= songEnd);
        } else if (event.status == 0xFF && event.data[0] == 0x06) {
          // Marker meta event; skip the type byte to get the text.
          markers.emplace_back(event.data.begin() + 1, event.data.end());
        }
      }
      // Every note on was matched by a note off on the same channel and pitch.
      for (auto& [key, count] : held) CHECK(count == 0);
    }
    // The song isn't silent.
    CHECK(notes > 0);
    // One marker per section, in order, with the names from sectionName in GenreTemplate.cpp.
    CHECK(markers.size() == plan.sections.size());
    for (size_t i = 0; i < markers.size() && i < plan.sections.size(); ++i) {
      CHECK(markers[i] == sectionName(plan.sections[i].type));
    }
  }
}

}  // namespace

// Runs every test by name. An exception counts as a failure instead of stopping the run, and
// the exit code is non-zero if anything failed, which is what ctest looks at.
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
