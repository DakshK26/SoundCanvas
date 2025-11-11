#pragma once

#include <vector>
#include <string>
#include <cstdint>

/**
 * Minimal Standard MIDI File (SMF) Format 1 writer
 * Supports multi-track MIDI with tempo, time signature, notes, program changes
 */

class MidiWriter {
public:
    MidiWriter(int ticksPerQuarter = 480);
    
    /**
     * Set global tempo in BPM (applies to all tracks)
     */
    void setTempo(float bpm);
    
    /**
     * Set time signature (default: 4/4)
     */
    void setTimeSignature(int numerator = 4, int denominator = 4);
    
    /**
     * Add a new track and return its track index
     */
    int addTrack(const std::string& name = "");
    
    /**
     * Add note on event
     * @param track Track index (from addTrack)
     * @param tick Absolute tick position
     * @param channel MIDI channel (0-15, channel 9 = drums)
     * @param note MIDI note number (0-127)
     * @param velocity Note velocity (1-127, 0 = note off)
     */
    void addNoteOn(int track, int tick, int channel, int note, int velocity);
    
    /**
     * Add note off event
     */
    void addNoteOff(int track, int tick, int channel, int note);
    
    /**
     * Add program change (instrument selection)
     */
    void addProgramChange(int track, int tick, int channel, int program);
    
    /**
     * Write the complete MIDI file
     */
    void write(const std::string& filepath);
    
private:
    struct MidiEvent {
        int tick;
        std::vector<uint8_t> data;
        
        bool operator<(const MidiEvent& other) const {
            return tick < other.tick;
        }
    };
    
    struct Track {
        std::string name;
        std::vector<MidiEvent> events;
    };
    
    int ticksPerQuarter_;
    float tempoBpm_;
    int timeSignatureNumerator_;
    int timeSignatureDenominator_;
    std::vector<Track> tracks_;
    
    // Internal helpers
    void writeVarLen(std::vector<uint8_t>& out, uint32_t value);
    void writeU16(std::vector<uint8_t>& out, uint16_t value);
    void writeU32(std::vector<uint8_t>& out, uint32_t value);
    std::vector<uint8_t> buildTrackData(int trackIndex);
};
