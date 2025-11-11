#include "SectionPlanner.hpp"
#include <algorithm>
#include <cmath>

SongPlan planSong(const ImageFeatures& features, 
                  const MusicParameters& params,
                  const GenreTemplate& genreTemplate) {
    
    SongPlan plan;
    plan.genre = genreTemplate.type;
    plan.tempoBpm = std::clamp(
        static_cast<int>(params.tempoBpm),
        genreTemplate.minTempo,
        genreTemplate.maxTempo
    );
    
    // Pick scale from genre preferences or use model's choice
    if (!genreTemplate.preferredScales.empty()) {
        // Use first preferred scale (could randomize later)
        plan.scaleType = genreTemplate.preferredScales[0];
    } else {
        plan.scaleType = params.scaleType;
    }
    
    // Calculate root note from base frequency
    float freq = params.baseFrequency;
    int midiNote = static_cast<int>(std::round(69.0 + 12.0 * std::log2(freq / 440.0)));
    plan.rootNote = std::clamp(midiNote, 48, 72);  // C3 to C5
    
    // Build section timeline
    int currentBar = 0;
    bool shouldAddDrop = params.energy >= genreTemplate.dropEnergyThreshold;
    
    for (const auto& sectionTemplate : genreTemplate.sectionPlan) {
        PlannedSection section;
        section.type = sectionTemplate.type;
        section.startBar = currentBar;
        section.bars = sectionTemplate.bars;
        section.energy = sectionTemplate.energyLevel;
        section.hasDrop = sectionTemplate.hasDropTrigger && shouldAddDrop;
        
        // Add automation based on section type
        section.filterSweep = (section.type == SectionType::BUILD);
        section.volumeBuild = (section.type == SectionType::BUILD);
        section.dropIntensity = section.hasDrop ? 1.0f : 0.0f;
        
        // For DROP sections, boost energy if image has high energy
        if (section.type == SectionType::DROP) {
            section.energy = std::min(1.0f, section.energy + params.energy * 0.3f);
        }
        
        plan.sections.push_back(section);
        currentBar += section.bars;
    }
    
    plan.totalBars = currentBar;
    
    // Determine which instruments to include based on overall energy
    for (const auto& layer : genreTemplate.layers) {
        if (params.energy >= layer.minEnergy) {
            plan.activeInstruments.push_back(layer.role);
        }
    }
    
    // Ensure minimum instruments (always have kick + bass + one melodic)
    if (std::find(plan.activeInstruments.begin(), plan.activeInstruments.end(), "kick") 
        == plan.activeInstruments.end()) {
        plan.activeInstruments.push_back("kick");
    }
    if (std::find(plan.activeInstruments.begin(), plan.activeInstruments.end(), "bass") 
        == plan.activeInstruments.end()) {
        plan.activeInstruments.push_back("bass");
    }
    
    return plan;
}

SongSpec songPlanToSpec(const SongPlan& plan) {
    SongSpec spec;
    
    spec.tempoBpm = plan.tempoBpm;
    spec.scaleType = plan.scaleType;
    spec.rootMidiNote = plan.rootNote;
    spec.totalBars = plan.totalBars;
    
    // Map genre to groove
    switch (plan.genre) {
        case GenreType::EDM_CHILL:
        case GenreType::RETROWAVE:
            spec.groove = GrooveType::CHILL;
            break;
        case GenreType::EDM_DROP:
            spec.groove = GrooveType::DRIVING;
            break;
        case GenreType::CINEMATIC:
            spec.groove = GrooveType::STRAIGHT;
            break;
    }
    
    // Convert planned sections to SongSpec sections
    for (const auto& plannedSec : plan.sections) {
        SectionSpec sec;
        sec.name = sectionTypeName(plannedSec.type);
        sec.bars = plannedSec.bars;
        sec.energy = plannedSec.energy;
        spec.sections.push_back(sec);
    }
    
    // Create tracks from active instruments
    // Map instrument roles to MIDI programs (simplified for now)
    std::map<std::string, int> instrumentPrograms = {
        {"kick", 36},
        {"snare", 38},
        {"hihat", 42},
        {"bass", 38},    // Synth bass
        {"lead", 81},    // Square lead
        {"pad", 89},     // Soft pad
        {"arp", 88},     // New Age pad (arp-like)
        {"pluck", 25},   // Acoustic guitar (pluck)
        {"fx", 99},      // FX
        {"strings", 49}, // String ensemble
        {"brass", 61},   // Brass section
        {"choir", 52},   // Choir
        {"piano", 0},    // Acoustic piano
        {"perc", 47}     // Timpani
    };
    
    for (const auto& instRole : plan.activeInstruments) {
        TrackSpec track;
        track.role = instRole;
        
        // Set MIDI program
        auto it = instrumentPrograms.find(instRole);
        track.midiProgram = (it != instrumentPrograms.end()) ? it->second : 0;
        
        // Set preset based on role
        if (instRole == "pad" || instRole == "fx") {
            track.preset = InstrumentPreset::SOFT_PAD;
        } else if (instRole == "lead" || instRole == "arp") {
            track.preset = InstrumentPreset::KEYS;
        } else if (instRole == "pluck" || instRole == "strings") {
            track.preset = InstrumentPreset::PLUCK;
        } else {
            track.preset = InstrumentPreset::KEYS;
        }
        
        // Set volume and complexity
        track.volume = 0.7f;
        track.complexity = 0.5f;
        
        spec.tracks.push_back(track);
    }
    
    // Default ambience and mood (could be derived from genre)
    spec.ambience = AmbienceType::NONE;  // Genre systems handle their own atmosphere
    spec.moodScore = 0.7f;
    
    return spec;
}
