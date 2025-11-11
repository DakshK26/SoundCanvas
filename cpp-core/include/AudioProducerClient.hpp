#ifndef AUDIO_PRODUCER_CLIENT_HPP
#define AUDIO_PRODUCER_CLIENT_HPP

#include <map>
#include <string>
#include <vector>

/**
 * Client for calling the audio-producer microservice
 * Handles multi-stem mixing and mastering
 */
class AudioProducerClient {
 public:
  /**
   * Constructor
   * @param baseUrl URL of the audio-producer service (e.g.,
   * "http://audio-producer:9001")
   */
  explicit AudioProducerClient(const std::string& baseUrl);

  /**
   * Produce final mixed and mastered track from MIDI stems
   *
   * @param stems Map of stem name -> MIDI file path
   *              e.g., {"kick": "/data/midi/kick.mid", "bass":
   * "/data/midi/bass.mid"}
   * @param outputPath Output WAV file path
   * @param genre Genre template name (e.g., "EDM_Drop", "EDM_Chill")
   * @param applyMastering Whether to apply mastering chain
   * @param applySidechain Whether to apply sidechain compression
   * @param sidechainTargets List of stems to apply sidechain to (e.g., {"bass",
   * "lead", "pad"})
   * @return true if successful, false otherwise
   */
  bool produceTrack(const std::map<std::string, std::string>& stems,
                    const std::string& outputPath,
                    const std::string& genre = "EDM_Drop",
                    bool applyMastering = true, bool applySidechain = true,
                    const std::vector<std::string>& sidechainTargets = {
                        "bass", "lead", "pad"});

  /**
   * Render single MIDI stem to WAV (no mixing/mastering)
   *
   * @param midiPath Input MIDI file path
   * @param outputPath Output WAV file path
   * @return true if successful
   */
  bool renderStem(const std::string& midiPath, const std::string& outputPath);

  /**
   * Health check
   * @return true if service is healthy
   */
  bool healthCheck();

 private:
  std::string baseUrl_;
  std::string host_;
  int port_;

  void parseUrl();
};

#endif  // AUDIO_PRODUCER_CLIENT_HPP
