#pragma once
#include <string>

// Forward declarations
struct StyleParameters;

/**
 * Audio Renderer Client
 * Calls the audio-renderer service to convert MIDI to WAV with ambience
 */
class AudioRendererClient {
 public:
  AudioRendererClient(const std::string& baseUrl);

  /**
   * Render MIDI file to WAV using FluidSynth with optional ambience
   *
   * @param midiPath Path to input MIDI file
   * @param outputPath Path for output WAV file
   * @param style Style parameters (contains ambience type and mood score)
   * @return true if successful, false otherwise
   */
  bool renderMidiToWav(const std::string& midiPath,
                       const std::string& outputPath,
                       const StyleParameters& style) const;

 private:
  std::string baseUrl_;
};
